from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from tiny_swarm_world.domain.ingress import TlsAuthorityMode
from tiny_swarm_world.infrastructure.adapters.ingress.local_tls_contract_resolver import (
    LocalTlsContractResolver,
    TlsContractConfigurationError,
)
from tiny_swarm_world.infrastructure.process import ProcessExecutionError, SubprocessProcessRunner


class TestLocalTlsContractResolver(unittest.TestCase):
    def test_managed_ca_signs_leaf_and_is_reused_byte_for_byte(self):
        if subprocess.run(("openssl", "version"), capture_output=True).returncode != 0:
            self.skipTest("openssl unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            resolver = self._resolver(state)

            first = resolver.resolve()
            before = {path: path.read_bytes() for path in state.iterdir() if path.is_file()}
            second = resolver.resolve()

            self.assertEqual(first.mode, TlsAuthorityMode.MANAGED)
            self.assertEqual(first.trust_bundle, state / "ca-bundle.pem")
            self.assertEqual(first.trust_bundle.read_bytes(), first.ca_certificate.read_bytes())
            self.assertEqual(first.lifecycle_fingerprint, second.lifecycle_fingerprint)
            self.assertEqual(before, {path: path.read_bytes() for path in state.iterdir() if path.is_file()})
            self.assertNotEqual(first.ca_certificate.read_bytes(), first.leaf_certificate.read_bytes())
            self.assertEqual(first.leaf_private_key.stat().st_mode & 0o777, 0o600)
            self.assertEqual(first.ca_private_key.stat().st_mode & 0o777, 0o600)

    def test_complete_external_material_has_precedence_without_state_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            managed = self._resolver(root / "external-source").resolve()
            target = root / "unused-managed-state"
            environment = {
                "TSW_TRAEFIK_CA_CERT_PATH": str(managed.ca_certificate),
                "TSW_TRAEFIK_TLS_CERT_PATH": str(managed.leaf_certificate),
                "TSW_TRAEFIK_TLS_KEY_PATH": str(managed.leaf_private_key),
            }

            contract = self._resolver(target, environment).resolve()

            self.assertEqual(contract.mode, TlsAuthorityMode.EXTERNAL)
            self.assertEqual(contract.trust_bundle, managed.ca_certificate)
            self.assertFalse(target.exists())

    def test_incomplete_external_material_fails_before_managed_state_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            resolver = self._resolver(
                state,
                {"TSW_TRAEFIK_CA_CERT_PATH": "/operator/ca.crt"},
            )

            with self.assertRaisesRegex(TlsContractConfigurationError, "Incomplete external"):
                resolver.resolve()

            self.assertFalse(state.exists())

    def test_invalid_existing_managed_state_fails_without_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            contract = self._resolver(state).resolve()
            original_hash = hashlib.sha256(contract.ca_certificate.read_bytes()).hexdigest()
            contract.leaf_certificate.write_text("invalid", encoding="utf-8")

            with self.assertRaisesRegex(TlsContractConfigurationError, "validation failed"):
                self._resolver(state).resolve()

            self.assertEqual(
                hashlib.sha256(contract.ca_certificate.read_bytes()).hexdigest(),
                original_hash,
            )

    def test_rejects_identical_ca_and_leaf_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._resolver(root / "source").resolve()
            source.leaf_certificate.write_bytes(source.ca_certificate.read_bytes())

            with self.assertRaisesRegex(TlsContractConfigurationError, "must differ"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_superdomain_san_instead_of_substring_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = LocalTlsContractResolver(
                state_root=root / "source",
                certificate_secret_name="tsw-cert",
                private_key_secret_name="tsw-key",
                environment={},
                ingress_dns_names=("tsw.local.evil", "*.tsw.local", "localhost"),
            ).resolve()

            with self.assertRaisesRegex(TlsContractConfigurationError, "SAN policy"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_external_certificate_with_extra_attacker_san(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = LocalTlsContractResolver(
                state_root=root / "source",
                certificate_secret_name="tsw-cert",
                private_key_secret_name="tsw-key",
                environment={},
                ingress_dns_names=(
                    "tsw.local",
                    "*.tsw.local",
                    "localhost",
                    "attacker.example",
                ),
            ).resolve()

            with self.assertRaisesRegex(TlsContractConfigurationError, "SAN policy"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_mismatched_leaf_private_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._resolver(root / "source").resolve()
            other = self._resolver(root / "other").resolve()
            source.leaf_private_key.write_bytes(other.leaf_private_key.read_bytes())

            with self.assertRaisesRegex(TlsContractConfigurationError, "do not match"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_leaf_signed_by_a_different_ca(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._resolver(root / "source").resolve()
            wrong_ca = self._resolver(root / "wrong-ca").resolve()
            source.ca_certificate.write_bytes(wrong_ca.ca_certificate.read_bytes())

            with self.assertRaisesRegex(TlsContractConfigurationError, "validation failed"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_near_expiry_ca_and_leaf_without_rotating_state(self):
        for target in ("ca_certificate", "leaf_certificate"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary) / "state"
                contract = self._resolver(state).resolve()
                before = {path.name: path.read_bytes() for path in state.iterdir() if path.is_file()}
                resolver = LocalTlsContractResolver(
                    state_root=state,
                    certificate_secret_name="tsw-cert",
                    private_key_secret_name="tsw-key",
                    environment={},
                    process_runner=_CheckendFailureRunner(target),
                )

                with self.assertRaisesRegex(TlsContractConfigurationError, "validation failed"):
                    resolver.resolve()

                self.assertEqual(
                    before,
                    {path.name: path.read_bytes() for path in state.iterdir() if path.is_file()},
                )
                self.assertTrue(contract.lifecycle_fingerprint)

    def test_rejects_adversarial_ca_and_leaf_extension_roles(self):
        cases = (
            ("ca_certificate", "keyUsage", "X509v3 Key Usage:\n Digital Signature", "CA signing role"),
            ("leaf_certificate", "basicConstraints", "X509v3 Basic Constraints:\n CA:TRUE", "server leaf role"),
            ("leaf_certificate", "extendedKeyUsage", "X509v3 Extended Key Usage:\n TLS Web Client Authentication", "server leaf role"),
        )
        for target, extension, output, expected in cases:
            with self.subTest(target=target, extension=extension), tempfile.TemporaryDirectory() as temporary:
                state = Path(temporary) / "state"
                self._resolver(state).resolve()
                resolver = LocalTlsContractResolver(
                    state_root=state,
                    certificate_secret_name="tsw-cert",
                    private_key_secret_name="tsw-key",
                    environment={},
                    process_runner=_ExtensionOverrideRunner(target, extension, output),
                )

                with self.assertRaisesRegex(TlsContractConfigurationError, expected):
                    resolver.resolve()

    def test_rejects_insecure_private_key_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._resolver(root / "source").resolve()
            source.leaf_private_key.chmod(0o644)

            with self.assertRaisesRegex(TlsContractConfigurationError, "owner-only"):
                self._external_resolver(root / "target", source).resolve()

    def test_rejects_conflicting_live_trust_bundle_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = self._resolver(
                root / "state",
                {"TSW_LIVE_TLS_CA_BUNDLE": str(root / "different-ca.pem")},
            )

            with self.assertRaisesRegex(TlsContractConfigurationError, "alias conflicts"):
                resolver.resolve()

    def test_rejects_managed_trust_bundle_drift_without_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            contract = self._resolver(state).resolve()
            contract.trust_bundle.write_text("different trust", encoding="utf-8")

            with self.assertRaisesRegex(TlsContractConfigurationError, "trust bundle differs"):
                self._resolver(state).resolve()

    def test_rejects_symlinked_tls_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._resolver(root / "source").resolve()
            original = source.ca_certificate.with_suffix(".original")
            source.ca_certificate.replace(original)
            source.ca_certificate.symlink_to(original)

            with self.assertRaisesRegex(TlsContractConfigurationError, "missing"):
                self._external_resolver(root / "target", source).resolve()

    @staticmethod
    def _resolver(state: Path, environment=None):
        return LocalTlsContractResolver(
            state_root=state,
            certificate_secret_name="tsw-cert",
            private_key_secret_name="tsw-key",
            environment={} if environment is None else environment,
        )

    @staticmethod
    def _external_resolver(state: Path, contract):
        return LocalTlsContractResolver(
            state_root=state,
            certificate_secret_name="tsw-cert",
            private_key_secret_name="tsw-key",
            environment={
                "TSW_TRAEFIK_CA_CERT_PATH": str(contract.ca_certificate),
                "TSW_TRAEFIK_TLS_CERT_PATH": str(contract.leaf_certificate),
                "TSW_TRAEFIK_TLS_KEY_PATH": str(contract.leaf_private_key),
            },
        )


class _CheckendFailureRunner:
    def __init__(self, target: str):
        self._target = target
        self._delegate = SubprocessProcessRunner()

    def run_text(self, args, **kwargs):
        if "-checkend" in args and any(str(value).endswith(self._target) for value in args):
            raise ProcessExecutionError(1)
        return self._delegate.run_text(args, **kwargs)

    def run_bytes(self, args, **kwargs):
        return self._delegate.run_bytes(args, **kwargs)


class _ExtensionOverrideRunner(_CheckendFailureRunner):
    def __init__(self, target: str, extension: str, output: str):
        super().__init__("never")
        self._extension = extension
        self._output = output
        self._extension_target = target

    def run_text(self, args, **kwargs):
        if (
            "-ext" in args
            and self._extension in args
            and any(str(value).endswith(self._extension_target) for value in args)
        ):
            return subprocess.CompletedProcess(args, 0, self._output, "")
        return super().run_text(args, **kwargs)
