from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Mapping

from tiny_swarm_world.application.ports.clients.port_infisical_cli import PortInfisicalCli
from tiny_swarm_world.application.ports.file_management.port_local_file_storage import (
    PortLocalFileStorage,
)
from tiny_swarm_world.domain.configuration.credential_resolution import (
    CredentialResolutionError,
    CredentialSource,
    ResolvedCredential,
)
from tiny_swarm_world.application.services.credential_resolution import (
    CREDENTIAL_SOURCE_MAP_ENVIRONMENT,
    CredentialResolutionService,
    CredentialResolutionSnapshot,
    decode_source_metadata,
)
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus

SecretClassification = Literal[
    "managed_secret",
    "external_user_secret",
    "placeholder_only",
    "false_positive",
    "blocker",
]
SecretPolicy = Literal["keep_existing", "rotate"]
REDACTED = "<redacted>"
DEFAULT_MANIFEST_PATH = Path("infra/config/secrets/infisical-secrets.yaml")
DEFAULT_EVIDENCE_DIR = Path(".tiny-swarm/evidence/secrets")
SECRET_KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9_]*(?:PASSWORD|TOKEN|SECRET|API_KEY|CREDENTIAL|HTPASSWD|KEY)[A-Z0-9_]*\b")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?P<key>[a-z_][a-z0-9_-]*)\s*[:=]\s*(?P<value>[^\n#]+)",
    re.IGNORECASE,
)
PLACEHOLDER_MARKERS = ("${", "{{", "<", "redacted", "placeholder", "changeme", "fake", "sample", "-password", "-secret", "-value")
SOURCE_MARKERS = ("internal_test_catalog", "external_user_secret", "managed_secret", "placeholder_only")
MANIFEST_TYPE_BY_SOURCE = {
    "internal_test_catalog": "managed_secret",
    "external_user_secret": "external_user_secret",
    "placeholder_only": "placeholder_only",
}
CONSUMER_REF_PATTERN = re.compile(r"^[a-z0-9][a-z0-9:._-]*$")
FALSE_POSITIVE_KEYS = ("PUBLIC_KEY", "RESOURCE_KEYS", "RAW_EVIDENCE_KEYS")
FALSE_POSITIVE_ASSIGNMENTS = (
    "INITIAL_PASSWORD",
    "KEY",
    "MISSING_SECRETS",
    "SECRET_CONTENT",
    "SECRET_ENV_FILE",
    "SECRET_ENVIRONMENT",
    "SECRET_FILE",
    "SECRET_NAME",
    "CREDENTIAL_NOTE",
    "PASSWORD_SOURCE",
    "SECRETS",
)
SCAN_SUFFIXES = {".env", ".yml", ".yaml", ".sh", ".py", ".groovy", ".conf", ".json", ".template", ".tpl"}
SCAN_DIRS = (".",)
SKIP_PARTS = {
    ".git",
    "__pycache__",
    ".venv",
    "bin",
    "include",
    "lib",
    "pydevd_attach_to_process",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".tiny-swarm",
    ".tiny-swarm-world",
    ".idea",
}


@dataclass(frozen=True)
class SecretManifestEntry:
    key: str
    service: str
    type: SecretClassification
    environment: str
    description: str
    source: str
    required: bool
    policy: SecretPolicy = "keep_existing"
    owner: str = ""
    storage: str = ""
    lifecycle: str = ""


@dataclass(frozen=True)
class SecretFinding:
    key: str
    classification: SecretClassification
    path: str
    line: int
    service: str = "unknown"
    redacted_value: str = REDACTED
    reason: str = ""


class SecretManagementBlocker(RuntimeError):
    def __init__(self, classification: str, message: str):
        super().__init__(message)
        self.classification = classification


class InfisicalSecretStore:
    def __init__(self, cli: PortInfisicalCli) -> None:
        self.cli = cli

    def ensure_scope(self, project: str, environment: str) -> None:
        self.cli.ensure_project_environment(project, environment)

    def secret_exists(self, key: str, *, project: str, environment: str) -> bool:
        return self.cli.secret_exists(key, project=project, environment=environment)

    def get_secret(self, key: str, *, project: str, environment: str) -> str | None:
        return self.cli.get_secret(key, project=project, environment=environment)

    def set_secret(self, key: str, value: str, *, project: str, environment: str) -> None:
        self.cli.set_secret(key, value, project=project, environment=environment)


class SecretRedactor:
    def __init__(self, known_values: tuple[str, ...] = ()) -> None:
        self.known_values = tuple(value for value in known_values if value)

    def redact(self, value: object) -> object:
        if isinstance(value, dict):
            return {str(key): self.redact(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        if isinstance(value, str):
            redacted = value
            for known_value in self.known_values:
                redacted = redacted.replace(known_value, REDACTED)
            if _is_sensitive_key_or_assignment(redacted):
                return _redact_assignment(redacted)
            return redacted
        return value


class SecretManifestRenderer:
    def __init__(self, storage: PortLocalFileStorage, manifest_path: Path = DEFAULT_MANIFEST_PATH) -> None:
        self.storage = storage
        self.manifest_path = manifest_path

    def run(self) -> tuple[SecretManifestEntry, ...]:
        payload = self.storage.load_yaml(self.manifest_path)
        if not isinstance(payload, dict) or not isinstance(payload.get("secrets"), list):
            raise SecretManagementBlocker("manifest_schema_invalid", "Secret manifest must contain a secrets list.")
        entries = tuple(_manifest_entry(item) for item in payload["secrets"])
        keys = [entry.key for entry in entries]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise SecretManagementBlocker("manifest_schema_invalid", f"Duplicate secret keys: {', '.join(duplicates)}")
        return entries


class SecretDiscoveryStep:
    verification_target_id = "deployment:managed-config-inventory"
    deployment_target_id = verification_target_id

    def __init__(
        self,
        *,
        storage: PortLocalFileStorage,
        repo_root: Path = Path("."),
        manifest_entries: tuple[SecretManifestEntry, ...] = (),
    ) -> None:
        self.storage = storage
        self.repo_root = repo_root
        self.manifest_entries = manifest_entries
        self._findings: tuple[SecretFinding, ...] = ()

    @property
    def findings(self) -> tuple[SecretFinding, ...]:
        return self._findings

    def run(self) -> tuple[SecretFinding, ...]:
        managed_keys = {entry.key: entry for entry in self.manifest_entries}
        findings: list[SecretFinding] = []
        snapshots = self.storage.scan_text_files(
            self.repo_root,
            suffixes=frozenset(SCAN_SUFFIXES),
            skip_parts=frozenset(SKIP_PARTS),
        )
        for snapshot in snapshots:
            for line_number, line in enumerate(snapshot.text.splitlines(), start=1):
                findings.extend(
                    _classify_line(snapshot.path, self.repo_root, line_number, line, managed_keys)
                )
        self._findings = tuple(findings)
        blockers = [finding for finding in self._findings if finding.classification == "blocker"]
        if blockers:
            blocker = blockers[0]
            raise SecretManagementBlocker("blocker", f"Unmanaged tracked secret-like value found at {blocker.path}:{blocker.line}")
        return self._findings

    def verify(self) -> VerificationResult:
        blockers = [finding for finding in self._findings if finding.classification == "blocker"]
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.BLOCKED if blockers else VerificationStatus.VERIFIED,
            message="Managed config inventory was classified with redacted values.",
            evidence={
                "phase": "verify",
                "discovered_count": str(len(self._findings)),
                "blocker_count": str(len(blockers)),
            },
        )


class InfisicalBootstrapStep:
    verification_target_id = "deployment:infisical-bootstrap-order"
    deployment_target_id = verification_target_id

    def __init__(self, bootstrap_step: object) -> None:
        self.bootstrap_step = bootstrap_step

    def run(self) -> None:
        run = getattr(self.bootstrap_step, "run")
        run()

    def verify(self) -> object:
        verify = getattr(self.bootstrap_step, "verify")
        return verify()


class InfisicalSecretSyncStep:
    verification_target_id = "deployment:infisical-sync"
    deployment_target_id = verification_target_id

    def __init__(
        self,
        *,
        cli: PortInfisicalCli,
        storage: PortLocalFileStorage,
        manifest_entries: tuple[SecretManifestEntry, ...],
        project: str = "tiny-swarm-world",
        environment: str = "local",
        process_environment: Mapping[str, str] | None = None,
    ) -> None:
        self.use_case = SecretSyncUseCase(
            store=InfisicalSecretStore(cli),
            storage=storage,
            manifest_entries=manifest_entries,
            project=project,
            environment=environment,
            process_environment=process_environment,
        )
        self.results: list[dict[str, str]] = []
        self.checked_secret_keys: tuple[str, ...] = ()
        self.synchronized_secret_keys: tuple[str, ...] = ()
        self.credential_sources: dict[str, CredentialSource] = {}

    def run(self) -> None:
        self.use_case.run()
        self.results = self.use_case.results
        self.checked_secret_keys = self.use_case.checked_secret_keys
        self.synchronized_secret_keys = self.use_case.synchronized_secret_keys
        self.credential_sources = dict(self.use_case.credential_sources)

    def verify(self) -> VerificationResult:
        return self.use_case.verify()


class SecretSyncUseCase:
    def __init__(
        self,
        *,
        store: InfisicalSecretStore,
        storage: PortLocalFileStorage,
        manifest_entries: tuple[SecretManifestEntry, ...],
        project: str = "tiny-swarm-world",
        environment: str = "local",
        process_environment: Mapping[str, str] | None = None,
    ) -> None:
        self.store = store
        self.storage = storage
        self.manifest_entries = manifest_entries
        self.project = project
        self.environment = environment
        self.process_environment = process_environment or {}
        self.credential_resolution_service = CredentialResolutionService()
        self.source_metadata = decode_source_metadata(
            self.process_environment.get(CREDENTIAL_SOURCE_MAP_ENVIRONMENT)
        )
        self.results: list[dict[str, str]] = []
        self.checked_secret_keys: tuple[str, ...] = ()
        self.synchronized_secret_keys: tuple[str, ...] = ()
        self.credential_sources: dict[str, CredentialSource] = {}

    def run(self) -> None:
        try:
            self.store.ensure_scope(self.project, self.environment)
        except Exception as exc:
            raise SecretManagementBlocker(
                "infisical_sync_failed",
                "Infisical secret sync failed while preparing scope.",
            ) from exc
        self._run_internal_test()

    def _run_internal_test(self) -> None:
        checked = []
        for entry in self.manifest_entries:
            snapshot = self._resolve_internal_test_entry(entry)
            resolution = snapshot.resolutions[entry.key]
            value = resolution.value
            if entry.required and not value:
                raise SecretManagementBlocker(
                    "blocker",
                    f"Required secret value is missing: {entry.key}",
                )
            self.credential_sources[entry.key] = resolution.source
            if entry.type == "external_user_secret":
                self.results.append(
                    _sync_result(
                        entry,
                        "verified_external_reference",
                        source=resolution.source,
                    )
                )
            else:
                self._sync_entry(entry, value, source=resolution.source)
            checked.append(entry.key)
        self.checked_secret_keys = tuple(checked)
        self.synchronized_secret_keys = tuple(
            result["key"]
            for result in self.results
            if result["sync_status"] in {"created", "updated", "kept_existing"}
        )

    def _resolve_internal_test_entry(self, entry: SecretManifestEntry) -> CredentialResolutionSnapshot:
        operator_value = self.process_environment.get(entry.key, "")
        if self.source_metadata.get(entry.key) is CredentialSource.DEFAULT:
            operator_value = ""
        secure_value = None if entry.type == "external_user_secret" else self._get_vault_value(entry)
        try:
            return self.credential_resolution_service.resolve_post_bootstrap(
                (entry.key,),
                operator_values={entry.key: operator_value},
                secure_values=({entry.key: secure_value} if secure_value else None),
            )
        except CredentialResolutionError as error:
            if not entry.required and not operator_value and not secure_value:
                return CredentialResolutionSnapshot({
                    entry.key: ResolvedCredential(
                        entry.key,
                        "",
                        CredentialSource.DEFAULT,
                    )
                })
            raise SecretManagementBlocker("blocker", str(error)) from error

    def _get_vault_value(self, entry: SecretManifestEntry) -> str | None:
        try:
            return self.store.get_secret(
                entry.key,
                project=self.project,
                environment=self.environment,
            )
        except Exception as exc:
            raise SecretManagementBlocker(
                "infisical_sync_failed",
                f"Infisical secret sync failed while reading key: {entry.key}",
            ) from exc

    def _sync_entry(
        self,
        entry: SecretManifestEntry,
        value: str,
        *,
        source: CredentialSource = CredentialSource.OPERATOR,
    ) -> None:
        if not value:
            self.results.append(
                _sync_result(entry, "skipped_missing_optional", source=source)
            )
            return
        exists = self._secret_exists(entry)
        if exists and entry.policy == "keep_existing":
            self.results.append(_sync_result(entry, "kept_existing", source=source))
            return
        self._set_entry(
            entry,
            value,
            status_if_existing="updated" if exists else "created",
            source=source,
        )

    def _secret_exists(self, entry: SecretManifestEntry) -> bool:
        try:
            return self.store.secret_exists(entry.key, project=self.project, environment=self.environment)
        except Exception as exc:
            raise SecretManagementBlocker(
                "infisical_sync_failed",
                f"Infisical secret sync failed while checking key: {entry.key}",
            ) from exc

    def _set_entry(
        self,
        entry: SecretManifestEntry,
        value: str,
        *,
        status_if_existing: str,
        source: CredentialSource = CredentialSource.OPERATOR,
    ) -> None:
        try:
            exists = self.store.secret_exists(entry.key, project=self.project, environment=self.environment)
            self.store.set_secret(entry.key, value, project=self.project, environment=self.environment)
        except Exception as exc:
            raise SecretManagementBlocker(
                "infisical_sync_failed",
                f"Infisical secret sync failed while writing key: {entry.key}",
            ) from exc
        self.results.append(
            _sync_result(
                entry,
                status_if_existing if exists else "created",
                source=source,
            )
        )

    def verify(self) -> VerificationResult:
        synced = [
            result
            for result in self.results
            if result["sync_status"] in {"created", "updated", "kept_existing", "verified_existing"}
        ]
        missing = [result for result in self.results if result["sync_status"] == "skipped_missing_optional"]
        return VerificationResult(
            target_id=InfisicalSecretSyncStep.verification_target_id,
            status=VerificationStatus.VERIFIED,
            message="Infisical managed entries were synchronized idempotently.",
            evidence={
                "phase": "verify",
                "checked_entry_count": str(len(self.checked_secret_keys)),
                "synchronized_entry_count": str(len(self.synchronized_secret_keys)),
                "synced_entry_count": str(len(synced)),
                "optional_missing_count": str(len(missing)),
                "project": self.project,
                "scope_name": self.environment,
                "source_counts": json.dumps(
                    {
                        source.value: sum(
                            selected is source
                            for selected in self.credential_sources.values()
                        )
                        for source in CredentialSource
                    },
                    sort_keys=True,
                ),
            },
        )


class SecretConsumptionVerifier:
    verification_target_id = "deployment:managed-config-consumption"
    deployment_target_id = verification_target_id

    def __init__(
        self,
        *,
        manifest_entries: tuple[SecretManifestEntry, ...],
        stack_environment: Mapping[str, Mapping[str, str]] | None = None,
        non_stack_consumer_refs: Mapping[str, str] | None = None,
    ) -> None:
        self.manifest_entries = manifest_entries
        self.stack_environment = dict(stack_environment or {})
        self.non_stack_consumer_refs = dict(sorted((non_stack_consumer_refs or {}).items()))
        manifest_keys = {entry.key for entry in manifest_entries}
        unknown_keys = sorted(set(self.non_stack_consumer_refs) - manifest_keys)
        if unknown_keys:
            raise ValueError(f"Unknown managed config consumer key: {unknown_keys[0]}")
        invalid_refs = sorted(
            key
            for key, consumer_ref in self.non_stack_consumer_refs.items()
            if not CONSUMER_REF_PATTERN.fullmatch(consumer_ref)
        )
        if invalid_refs:
            raise ValueError(f"Invalid managed config consumer reference: {invalid_refs[0]}")
        self.report: list[dict[str, str]] = []

    def run(self) -> None:
        consumer_refs = {
            key: f"deployment:{stack_name}-stack"
            for stack_name, values in sorted(self.stack_environment.items())
            for key in sorted(values)
        }
        consumer_refs.update(self.non_stack_consumer_refs)
        self.report = [
            {
                "key": entry.key,
                "service": entry.service,
                "consumer_status": (
                    "configured"
                    if entry.key in consumer_refs or not entry.required
                    else "not_observed"
                ),
                "consumer_ref": consumer_refs.get(
                    entry.key,
                    "not_required" if not entry.required else "not_observed",
                ),
            }
            for entry in self.manifest_entries
        ]

    def verify(self) -> VerificationResult:
        missing = [item for item in self.report if item["consumer_status"] == "not_observed"]
        status = VerificationStatus.BLOCKED if missing else VerificationStatus.VERIFIED
        message = (
            "Required managed config consumption references are missing."
            if missing
            else "Managed config consumption references were verified without exposing values."
        )
        evidence = {
            "phase": "verify",
            "configured_ref_count": str(len(self.report)),
            "missing_required_count": str(len(missing)),
        }
        if missing:
            evidence["reason"] = "required_consumer_missing"
        return VerificationResult(
            target_id=self.verification_target_id,
            status=status,
            message=message,
            evidence=evidence,
        )


class SecretEvidenceWriter:
    verification_target_id = "deployment:managed-config-evidence"
    deployment_target_id = verification_target_id

    def __init__(
        self,
        *,
        storage: PortLocalFileStorage,
        evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
        discovery: SecretDiscoveryStep,
        sync: InfisicalSecretSyncStep,
        consumption: SecretConsumptionVerifier,
    ) -> None:
        self.storage = storage
        self.evidence_dir = evidence_dir
        self.discovery = discovery
        self.sync = sync
        self.consumption = consumption

    def run(self) -> None:
        now = datetime.now(UTC).isoformat()
        inventory = {
            "generated_at": now,
            "findings": [finding.__dict__ for finding in self.discovery.findings],
        }
        sync_result = {
            "checked_secret_keys": list(self.sync.checked_secret_keys),
            "credential_sources": {
                key: source.value
                for key, source in sorted(self.sync.credential_sources.items())
            },
            "generated_at": now,
            "results": self.sync.results,
            "synchronized_secret_keys": list(self.sync.synchronized_secret_keys),
        }
        consumption_lines = ["# Secret Consumption Report", ""]
        for item in self.consumption.report:
            consumption_lines.append(
                f"- {item['key']} ({item['service']}): "
                f"{item['consumer_status']} [{item['consumer_ref']}]"
            )
        self.storage.write_text(
            self.evidence_dir / "secret-inventory.json",
            json.dumps(inventory, indent=2, sort_keys=True),
            private=True,
        )
        self.storage.write_text(
            self.evidence_dir / "infisical-sync-result.json",
            json.dumps(sync_result, indent=2, sort_keys=True),
            private=True,
        )
        self.storage.write_text(
            self.evidence_dir / "secret-consumption-report.md",
            "\n".join(consumption_lines) + "\n",
            private=True,
        )

    def verify(self) -> VerificationResult:
        paths = ("secret-inventory.json", "infisical-sync-result.json", "secret-consumption-report.md")
        existing = [name for name in paths if self.storage.exists(self.evidence_dir / name)]
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.VERIFIED if len(existing) == len(paths) else VerificationStatus.BLOCKED,
            message="Sanitized managed config evidence files were written.",
            evidence={"phase": "verify", "artifact_count": str(len(existing))},
        )


def _manifest_entry(item: object) -> SecretManifestEntry:
    if not isinstance(item, dict):
        raise SecretManagementBlocker("manifest_schema_invalid", "Secret manifest entries must be mappings.")
    key = str(item.get("key", ""))
    if not re.fullmatch(r"TSW_[A-Z0-9]+(?:_[A-Z0-9]+)+", key):
        raise SecretManagementBlocker("manifest_schema_invalid", f"Invalid TSW secret key: {key}")
    entry_type = str(item.get("type", ""))
    if entry_type not in {"managed_secret", "external_user_secret", "placeholder_only"}:
        raise SecretManagementBlocker("manifest_schema_invalid", f"Invalid secret type for {key}: {entry_type}")
    policy = str(item.get("policy", "keep_existing"))
    if policy not in {"keep_existing", "rotate"}:
        raise SecretManagementBlocker("manifest_schema_invalid", f"Invalid secret policy for {key}: {policy}")
    source = str(item.get("source", ""))
    expected_type = MANIFEST_TYPE_BY_SOURCE.get(source)
    if expected_type is not None and entry_type != expected_type:
        raise SecretManagementBlocker(
            "manifest_schema_invalid",
            f"Secret type/source mismatch for {key}: {entry_type}/{source}",
        )
    return SecretManifestEntry(
        key=key,
        service=str(item.get("service", "")),
        type=entry_type,  # type: ignore[arg-type]
        environment=str(item.get("environment", "local")),
        description=str(item.get("description", "")),
        source=source,
        required=bool(item.get("required", False)),
        policy=policy,  # type: ignore[arg-type]
        owner=str(item.get("owner", _manifest_owner(source))),
        storage=str(item.get("storage", _manifest_storage(source))),
        lifecycle=str(item.get("lifecycle", _manifest_lifecycle(source))),
    )


def _manifest_owner(source: str) -> str:
    if source == "external_user_secret":
        return "operator"
    if source == "internal_test_catalog":
        return "credential_catalog"
    return "unknown"


def _manifest_storage(source: str) -> str:
    if source == "external_user_secret":
        return "external_docker_secret_or_operator_env"
    if source == "internal_test_catalog":
        return "catalog_or_operator_override"
    return "unknown"


def _manifest_lifecycle(source: str) -> str:
    if source == "external_user_secret":
        return "operator_created_and_rotated"
    if source == "internal_test_catalog":
        return "deterministic_catalog_value_or_explicit_override"
    return "unknown"


def _classify_line(path: Path, repo_root: Path, line_number: int, line: str, managed_keys: dict[str, SecretManifestEntry]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    relative = path.relative_to(repo_root).as_posix()
    for key in SECRET_KEY_PATTERN.findall(line):
        finding = _classify_secret_key(key, relative, line_number, managed_keys)
        if finding is not None:
            findings.append(finding)
    assignment = SECRET_ASSIGNMENT_PATTERN.search(line)
    if assignment:
        key = assignment.group("key")
        if not _is_secretish_name(key):
            return findings
        value = assignment.group("value").strip().strip('"\'')
        classification = _classify_secret_assignment(path, relative, line, key, value, managed_keys)
        findings.append(SecretFinding(key, classification, relative, line_number, redacted_value=REDACTED))
    return findings


def _classify_secret_key(
    key: str,
    relative: str,
    line_number: int,
    managed_keys: dict[str, SecretManifestEntry],
) -> SecretFinding | None:
    if any(false_key in key for false_key in FALSE_POSITIVE_KEYS):
        return SecretFinding(key, "false_positive", relative, line_number, reason="safe_symbol_name")
    if key in managed_keys:
        return SecretFinding(key, managed_keys[key].type, relative, line_number, service=managed_keys[key].service)
    if key.startswith("TSW_"):
        return SecretFinding(key, "external_user_secret", relative, line_number, reason="unmanaged_tsw_secret_reference")
    return None


def _classify_secret_assignment(
    path: Path,
    relative: str,
    line: str,
    key: str,
    value: str,
    managed_keys: dict[str, SecretManifestEntry],
) -> SecretClassification:
    if key in managed_keys or value in managed_keys or "_operator_secret_value" in value:
        return "managed_secret"
    if value.startswith("${") or "System.getenv" in value:
        return "placeholder_only"
    if key.upper() in FALSE_POSITIVE_ASSIGNMENTS:
        return "false_positive"
    if _is_secret_reference_assignment_key(key):
        return "placeholder_only"
    if any(marker in value.lower() for marker in SOURCE_MARKERS + PLACEHOLDER_MARKERS):
        return "placeholder_only"
    if relative.startswith("tests/") and ("assert" in line or "operator_credential" in line):
        return "placeholder_only"
    if path.suffix == ".py" and not value.startswith(("\"", "'")):
        return "false_positive"
    if value.startswith("/"):
        return "false_positive"
    if value and len(value) >= 6:
        return "blocker"
    return "false_positive"


def _is_secretish_name(key: str) -> bool:
    normalized = key.upper().replace("-", "_")
    if any(part in normalized for part in ("PASSWORD", "TOKEN", "SECRET", "API_KEY", "CREDENTIAL", "HTPASSWD")):
        return True
    return normalized.endswith("_KEY") and not normalized.endswith(("BY_KEY", "_KEYS"))


def _is_secret_reference_assignment_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized.endswith("_item_ref")


def _is_sensitive_key_or_assignment(value: str) -> bool:
    return bool(SECRET_ASSIGNMENT_PATTERN.search(value) or SECRET_KEY_PATTERN.search(value))


def _redact_assignment(value: str) -> str:
    return SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group('key')}={REDACTED}", value)


def _sync_result(
    entry: SecretManifestEntry,
    status: str,
    *,
    source: CredentialSource = CredentialSource.OPERATOR,
) -> dict[str, str]:
    return {
        "key": entry.key,
        "service": entry.service,
        "source": source.value,
        "source_type": entry.source,
        "sync_status": status,
    }
