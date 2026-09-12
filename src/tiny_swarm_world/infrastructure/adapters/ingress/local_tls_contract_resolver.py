from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from tiny_swarm_world.domain.ingress.tls_contract import (
    ResolvedTlsContract,
    TlsAuthorityMode,
)
from tiny_swarm_world.infrastructure.process import (
    ProcessRunner,
    ProcessRunnerError,
    SubprocessProcessRunner,
)

_EXTERNAL_PATH_KEYS = (
    "TSW_TRAEFIK_CA_CERT_PATH",
    "TSW_TRAEFIK_TLS_CERT_PATH",
    "TSW_TRAEFIK_TLS_KEY_PATH",
)
_OPTIONAL_CA_KEY = "TSW_TRAEFIK_CA_KEY_PATH"
_MANAGED_FILENAMES = {
    "ca_certificate": "ca.crt",
    "ca_private_key": "ca.key",
    "leaf_certificate": "tls.crt",
    "leaf_private_key": "tls.key",
    "trust_bundle": "ca-bundle.pem",
}


class TlsContractConfigurationError(RuntimeError):
    pass


class LocalTlsContractResolver:
    """Resolve external PKI or a persistent, locally managed CA and leaf."""

    def __init__(
        self,
        *,
        state_root: Path,
        certificate_secret_name: str,
        private_key_secret_name: str,
        environment: Mapping[str, str] | None = None,
        ingress_dns_names: Sequence[str] = ("tsw.local", "*.tsw.local", "localhost"),
        openssl: str = "openssl",
        process_runner: ProcessRunner | None = None,
    ) -> None:
        self._state_root = state_root.expanduser().resolve()
        self._certificate_secret_name = certificate_secret_name
        self._private_key_secret_name = private_key_secret_name
        self._environment = dict(os.environ if environment is None else environment)
        self._ingress_dns_names = tuple(dict.fromkeys(ingress_dns_names))
        self._openssl = openssl
        self._process_runner = process_runner or SubprocessProcessRunner()

    def resolve(self) -> ResolvedTlsContract:
        external = self._external_paths()
        if external is not None:
            return self._validated_contract(TlsAuthorityMode.EXTERNAL, external)

        paths = {name: self._state_root / filename for name, filename in _MANAGED_FILENAMES.items()}
        self._validate_trust_alias(paths["trust_bundle"])
        self._state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._state_root.chmod(0o700)
        if any(path.exists() for path in paths.values()):
            if not all(path.is_file() for path in paths.values()):
                raise TlsContractConfigurationError(
                    "Managed TLS state is incomplete; explicit recovery is required"
                )
        else:
            self._generate_managed(paths)
        return self._validated_contract(TlsAuthorityMode.MANAGED, paths)

    def _external_paths(self) -> dict[str, Path] | None:
        configured = {key: self._environment.get(key, "").strip() for key in _EXTERNAL_PATH_KEYS}
        optional_ca_key = self._environment.get(_OPTIONAL_CA_KEY, "").strip()
        if not any(configured.values()) and not optional_ca_key:
            return None
        missing = [key for key, value in configured.items() if not value]
        if missing:
            raise TlsContractConfigurationError(
                "Incomplete external TLS configuration: " + ", ".join(sorted(missing))
            )
        paths = {
            "ca_certificate": Path(configured["TSW_TRAEFIK_CA_CERT_PATH"]).expanduser().absolute(),
            "leaf_certificate": Path(configured["TSW_TRAEFIK_TLS_CERT_PATH"]).expanduser().absolute(),
            "leaf_private_key": Path(configured["TSW_TRAEFIK_TLS_KEY_PATH"]).expanduser().absolute(),
        }
        paths["trust_bundle"] = paths["ca_certificate"]
        if optional_ca_key:
            paths["ca_private_key"] = Path(optional_ca_key).expanduser().absolute()
        return paths

    def _generate_managed(self, paths: dict[str, Path]) -> None:
        with tempfile.TemporaryDirectory(dir=self._state_root, prefix=".tls-") as temporary:
            root = Path(temporary)
            generated = {
                name: root / filename
                for name, filename in _MANAGED_FILENAMES.items()
            }
            extension = root / "leaf.ext"
            extension.write_text(
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature,keyEncipherment\n"
                "extendedKeyUsage=serverAuth\n"
                f"subjectAltName={','.join(f'DNS:{name}' for name in self._ingress_dns_names)}\n",
                encoding="utf-8",
            )
            self._run((self._openssl, "genrsa", "-out", str(generated["ca_private_key"]), "3072"))
            self._run((
                self._openssl, "req", "-x509", "-new", "-sha256", "-days", "3650",
                "-key", str(generated["ca_private_key"]), "-subj", "/CN=Tiny Swarm World Local CA",
                "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign",
                "-out", str(generated["ca_certificate"]),
            ))
            self._run((self._openssl, "genrsa", "-out", str(generated["leaf_private_key"]), "2048"))
            request = root / "tls.csr"
            self._run((
                self._openssl, "req", "-new", "-sha256", "-key", str(generated["leaf_private_key"]),
                "-subj", "/CN=tsw.local", "-out", str(request),
            ))
            self._run((
                self._openssl, "x509", "-req", "-sha256", "-days", "825", "-in", str(request),
                "-CA", str(generated["ca_certificate"]), "-CAkey", str(generated["ca_private_key"]),
                "-CAcreateserial", "-extfile", str(extension), "-out", str(generated["leaf_certificate"]),
            ))
            generated["trust_bundle"].write_bytes(generated["ca_certificate"].read_bytes())
            for name, destination in paths.items():
                generated[name].chmod(0o600 if name.endswith("private_key") else 0o644)
                generated[name].replace(destination)

    def _validated_contract(
        self, mode: TlsAuthorityMode, paths: Mapping[str, Path]
    ) -> ResolvedTlsContract:
        required = ("ca_certificate", "leaf_certificate", "leaf_private_key", "trust_bundle")
        ca_key = paths.get("ca_private_key")
        for name in (*required, *(("ca_private_key",) if ca_key is not None else ())):
            path = paths[name]
            try:
                file_stat = path.lstat()
            except OSError as error:
                raise TlsContractConfigurationError(f"TLS material is missing: {name}") from error
            if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode):
                raise TlsContractConfigurationError(f"TLS material is missing: {name}")
        for name in ("leaf_private_key", "ca_private_key"):
            private_path = paths.get(name)
            if private_path is not None and private_path.stat().st_mode & 0o077:
                raise TlsContractConfigurationError("TLS private-key permissions are not owner-only")
        snapshots = {name: path.read_bytes() for name, path in paths.items()}
        if snapshots["ca_certificate"] == snapshots["leaf_certificate"]:
            raise TlsContractConfigurationError("CA and ingress leaf certificates must differ")
        if snapshots["trust_bundle"] != snapshots["ca_certificate"]:
            raise TlsContractConfigurationError("Canonical trust bundle differs from selected CA")
        with tempfile.TemporaryDirectory(prefix="tsw-tls-validate-") as temporary:
            snapshot_paths: dict[str, Path] = {}
            for name, content in snapshots.items():
                snapshot_path = Path(temporary) / name
                snapshot_path.write_bytes(content)
                snapshot_path.chmod(0o600)
                snapshot_paths[name] = snapshot_path
            self._validate_snapshot(snapshot_paths)
        self._validate_trust_alias(paths["trust_bundle"])
        fingerprint = hashlib.sha256(
            snapshots["ca_certificate"] + snapshots["leaf_certificate"]
        ).hexdigest()
        return ResolvedTlsContract(
            mode=mode,
            ca_certificate=paths["ca_certificate"],
            ca_private_key=paths.get("ca_private_key"),
            leaf_certificate=paths["leaf_certificate"],
            leaf_private_key=paths["leaf_private_key"],
            trust_bundle=paths["trust_bundle"],
            certificate_secret_name=self._certificate_secret_name,
            private_key_secret_name=self._private_key_secret_name,
            lifecycle_fingerprint=fingerprint,
            certificate_bytes=snapshots["leaf_certificate"],
            private_key_bytes=snapshots["leaf_private_key"],
        )

    def _validate_snapshot(self, paths: Mapping[str, Path]) -> None:
        ca_basic = self._certificate_extension(paths["ca_certificate"], "basicConstraints")
        ca_usage = self._certificate_extension(paths["ca_certificate"], "keyUsage")
        leaf_basic = self._certificate_extension(paths["leaf_certificate"], "basicConstraints")
        leaf_usage = self._certificate_extension(paths["leaf_certificate"], "keyUsage")
        leaf_extended = self._certificate_extension(paths["leaf_certificate"], "extendedKeyUsage")
        if "CA:TRUE" not in ca_basic or "Certificate Sign" not in ca_usage:
            raise TlsContractConfigurationError("Selected CA certificate lacks CA signing role")
        if "CA:FALSE" not in leaf_basic:
            raise TlsContractConfigurationError("Ingress certificate lacks server leaf role")
        if "Digital Signature" not in leaf_usage or "Key Encipherment" not in leaf_usage:
            raise TlsContractConfigurationError("Ingress certificate key usage is incomplete")
        if "TLS Web Server Authentication" not in leaf_extended:
            raise TlsContractConfigurationError("Ingress certificate lacks server leaf role")
        self._run((
            self._openssl, "verify", "-x509_strict", "-purpose", "sslserver", "-CAfile",
            str(paths["ca_certificate"]), str(paths["leaf_certificate"]),
        ))
        for name in ("ca_certificate", "leaf_certificate"):
            self._run((self._openssl, "x509", "-checkend", "86400", "-noout", "-in", str(paths[name])))
        san_text = self._certificate_extension(paths["leaf_certificate"], "subjectAltName")
        actual_sans = frozenset(re.findall(r"DNS:([^,\s]+)", san_text))
        if actual_sans != frozenset(self._ingress_dns_names):
            raise TlsContractConfigurationError("Ingress certificate SAN policy does not match")
        leaf_key_public = self._run((self._openssl, "pkey", "-pubout", "-in", str(paths["leaf_private_key"]))).stdout
        leaf_public = self._certificate_public_key(paths["leaf_certificate"])
        ca_public = self._certificate_public_key(paths["ca_certificate"])
        if leaf_key_public != leaf_public:
            raise TlsContractConfigurationError("Ingress certificate and private key do not match")
        if ca_public == leaf_public:
            raise TlsContractConfigurationError("CA and ingress leaf keys must differ")
        ca_key = paths.get("ca_private_key")
        if ca_key is not None:
            ca_key_public = self._run((self._openssl, "pkey", "-pubout", "-in", str(ca_key))).stdout
            if ca_key_public != ca_public:
                raise TlsContractConfigurationError("CA certificate and private key do not match")

    def _certificate_extension(self, path: Path, extension: str) -> str:
        return self._run((self._openssl, "x509", "-noout", "-ext", extension, "-in", str(path))).stdout

    def _certificate_public_key(self, path: Path) -> str:
        return self._run((self._openssl, "x509", "-pubkey", "-noout", "-in", str(path))).stdout

    def _validate_trust_alias(self, trust_bundle: Path) -> None:
        alias = self._environment.get("TSW_LIVE_TLS_CA_BUNDLE", "").strip()
        if alias and Path(alias).expanduser().resolve() != trust_bundle.resolve():
            raise TlsContractConfigurationError("TLS trust-bundle alias conflicts with canonical contract")

    def _run(self, command: tuple[str, ...]):
        try:
            return self._process_runner.run_text(command, check=True)
        except ProcessRunnerError as error:
            raise TlsContractConfigurationError("TLS material validation failed") from error
