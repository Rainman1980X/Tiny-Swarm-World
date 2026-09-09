import json
import tempfile
import unittest
from pathlib import Path

from tests.support.sonar_safe_literals import operator_credential, sample_text

from tiny_swarm_world.application.services.deployment.secret_management import (
    InfisicalSecretSyncStep,
    InfisicalSecretStore,
    SecretConsumptionVerifier,
    SecretDiscoveryStep,
    SecretEvidenceWriter,
    SecretManagementBlocker,
    SecretManifestEntry,
    SecretManifestRenderer,
    SecretRedactor,
    SecretSyncUseCase,
)
from tiny_swarm_world.infrastructure.adapters.file_management.local_file_storage import (
    LocalFileStorage,
)

_PULSAR_COMPOSE_FIXTURE = Path("infra/config/compose/pulsar/docker-compose.yml")
_STORAGE = LocalFileStorage()


class TestSecretManagement(unittest.TestCase):
    def test_manifest_schema_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "infisical-secrets.yaml"
            manifest.write_text(
                "secrets:\n"
                "  - key: TSW_POSTGRES_PASSWORD\n"
                "    service: postgres\n"
                "    type: managed_secret\n"
                "    environment: local\n"
                "    description: PostgreSQL password\n"
                "    source: internal_test_catalog\n"
                "    required: true\n",
                encoding="utf-8",
            )

            entries = SecretManifestRenderer(_STORAGE, manifest).run()

            self.assertEqual(entries[0].key, "TSW_POSTGRES_PASSWORD")
            self.assertEqual(entries[0].policy, "keep_existing")

    def test_removed_manifest_types_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "infisical-secrets.yaml"
            manifest.write_text(
                "secrets:\n"
                "  - key: TSW_OLD_PASSWORD\n"
                "    service: old\n"
                "    type: generated_secret\n"
                "    source: obsolete\n"
                "    required: false\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SecretManagementBlocker, "Invalid secret type"):
                SecretManifestRenderer(_STORAGE, manifest).run()

    def test_manifest_type_and_source_contract_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "infisical-secrets.yaml"
            manifest.write_text(
                "secrets:\n"
                "  - key: TSW_MISMATCHED_PASSWORD\n"
                "    service: test\n"
                "    type: external_user_secret\n"
                "    source: internal_test_catalog\n"
                "    required: false\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SecretManagementBlocker, "type/source mismatch"):
                SecretManifestRenderer(_STORAGE, manifest).run()

    def test_unknown_manifest_source_defaults_to_unknown_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "infisical-secrets.yaml"
            manifest.write_text(
                "secrets:\n"
                "  - key: TSW_RESERVED_PASSWORD\n"
                "    service: reserved\n"
                "    type: managed_secret\n"
                "    source: reserved_source\n"
                "    required: false\n",
                encoding="utf-8",
            )

            entry = SecretManifestRenderer(_STORAGE, manifest).run()[0]

        self.assertEqual(entry.owner, "unknown")
        self.assertEqual(entry.storage, "unknown")
        self.assertEqual(entry.lifecycle, "unknown")

    def test_committed_manifest_tracks_traefik_tls_secret_names_without_values(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        entries_by_key = {entry.key: entry for entry in entries}

        for key in (
            "TSW_TRAEFIK_TLS_CERT_SECRET_NAME",
            "TSW_TRAEFIK_TLS_KEY_SECRET_NAME",
            "TSW_TRAEFIK_GUI_USERS_SECRET_NAME",
        ):
            with self.subTest(key=key):
                entry = entries_by_key[key]
                self.assertEqual(entry.service, "traefik")
                self.assertEqual(entry.type, "external_user_secret")
                self.assertEqual(entry.source, "external_user_secret")
                self.assertTrue(entry.required)
                self.assertNotIn("BEGIN", entry.description)
                self.assertNotIn("REDACTED", entry.description)

    def test_missing_traefik_gui_external_secret_reference_blocks(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        gui_entry = next(
            entry for entry in entries if entry.key == "TSW_TRAEFIK_GUI_USERS_SECRET_NAME"
        )
        sync = InfisicalSecretSyncStep(
            cli=_FakeInfisicalCli(),
            storage=_STORAGE,
            manifest_entries=(gui_entry,),
        )

        with self.assertRaises(SecretManagementBlocker):
            sync.run()

    def test_committed_manifest_marks_infisical_redis_password_required(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        entries_by_key = {entry.key: entry for entry in entries}

        entry = entries_by_key["TSW_INFISICAL_REDIS_PASSWORD"]

        self.assertEqual(entry.service, "infisical")
        self.assertEqual(entry.type, "managed_secret")
        self.assertEqual(entry.source, "internal_test_catalog")
        self.assertTrue(entry.required)

    def test_manifest_entries_expose_ownership_storage_and_lifecycle(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        entries_by_key = {entry.key: entry for entry in entries}

        generated = entries_by_key["TSW_NEXUS_ADMIN_PASSWORD"]
        external = entries_by_key["TSW_TRAEFIK_TLS_CERT_SECRET_NAME"]
        bootstrap = entries_by_key["TSW_INFISICAL_LOGIN_EMAIL"]

        self.assertEqual(generated.owner, "credential_catalog")
        self.assertEqual(generated.storage, "catalog_or_operator_override")
        self.assertEqual(generated.lifecycle, "deterministic_catalog_value_or_explicit_override")
        self.assertEqual(external.owner, "operator")
        self.assertEqual(external.storage, "external_docker_secret_or_operator_env")
        self.assertEqual(external.lifecycle, "operator_created_and_rotated")
        self.assertEqual(bootstrap.owner, "credential_catalog")
        self.assertEqual(bootstrap.storage, "catalog_or_operator_override")
        self.assertEqual(bootstrap.lifecycle, "deterministic_catalog_value_or_explicit_override")

    def test_committed_manifest_tracks_required_infisical_login_identity(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        entries_by_key = {entry.key: entry for entry in entries}

        entry = entries_by_key["TSW_INFISICAL_LOGIN_EMAIL"]

        self.assertEqual(entry.service, "infisical")
        self.assertEqual(entry.type, "managed_secret")
        self.assertEqual(entry.source, "internal_test_catalog")
        self.assertTrue(entry.required)

    def test_pulsar_compose_bootstrap_does_not_create_secret_inventory_blocker(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_repo_fixture(root, "docker-compose.yml", _PULSAR_COMPOSE_FIXTURE.read_text(encoding="utf-8"))
            discovery = SecretDiscoveryStep(
                storage=_STORAGE,
                repo_root=root,
                manifest_entries=entries,
            )

            findings = discovery.run()

        self.assertFalse([finding for finding in findings if finding.classification == "blocker"])

    def test_secret_discovery_classifies_managed_placeholder_and_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docker-compose.yml").write_text(
                "POSTGRES_PASSWORD: ${TSW_POSTGRES_PASSWORD}\n"
                "password: " + "admin" + "Password123" + "\\n",
                encoding="utf-8",
            )
            discovery = SecretDiscoveryStep(
                storage=_STORAGE,
                repo_root=root,
                manifest_entries=(_entry("TSW_POSTGRES_PASSWORD"),),
            )

            with self.assertRaises(SecretManagementBlocker):
                discovery.run()

            classifications = {finding.classification for finding in discovery.findings}
            self.assertIn("managed_secret", classifications)
            self.assertIn("blocker", classifications)

    def test_secret_discovery_treats_credential_item_refs_as_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_repo_fixture(
                root,
                "ports.yaml",
                "credential_item_ref: platform/portainer\n"
                'credential_note: "Open Infisical item"\n',
            )
            discovery = SecretDiscoveryStep(storage=_STORAGE, repo_root=root)

            findings = discovery.run()

        classifications = {finding.key: finding.classification for finding in findings}
        self.assertEqual(classifications["credential_item_ref"], "placeholder_only")
        self.assertEqual(classifications["credential_note"], "false_positive")
        self.assertNotIn("blocker", set(classifications.values()))

    def test_secret_discovery_treats_bootstrap_password_source_as_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_repo_fixture(
                root,
                "services.yml",
                'password_source: "resolved_bootstrap_input"\n',
            )
            discovery = SecretDiscoveryStep(storage=_STORAGE, repo_root=root)

            findings = discovery.run()

        self.assertEqual(findings[0].classification, "false_positive")
        self.assertNotIn("blocker", {finding.classification for finding in findings})

    def test_redactor_redacts_values_and_assignments(self):
        redactor = SecretRedactor((operator_credential(),))
        key = sample_text("PASS", "WORD")

        redacted = redactor.redact({"line": f"{key}={operator_credential()}", "safe": "hello"})

        self.assertEqual(redacted["line"], f"{key}=<redacted>")
        self.assertEqual(redacted["safe"], "hello")

    def test_infisical_sync_creates_missing_and_keeps_existing(self):
        with tempfile.TemporaryDirectory():
            cli = _FakeInfisicalCli(existing={"TSW_EXISTING_PASSWORD"})
            sync = InfisicalSecretSyncStep(
                cli=cli,
                storage=_STORAGE,
                manifest_entries=(
                    _entry("TSW_NEW_PASSWORD"),
                    _entry("TSW_EXISTING_PASSWORD"),
                ),
                process_environment={
                    "TSW_NEW_PASSWORD": "new-value",
                    "TSW_EXISTING_PASSWORD": "existing-value",
                },
            )

            sync.run()

            statuses = {item["key"]: item["sync_status"] for item in sync.results}
            self.assertEqual(statuses["TSW_NEW_PASSWORD"], "created")
            self.assertEqual(statuses["TSW_EXISTING_PASSWORD"], "kept_existing")
            self.assertIn("TSW_NEW_PASSWORD", cli.values)

    def test_infisical_sync_uses_api_client_even_when_local_cli_is_missing(self):
        with tempfile.TemporaryDirectory():
            cli = _FakeInfisicalCli(available=False)
            sync = InfisicalSecretSyncStep(
                cli=cli,
                storage=_STORAGE,
                manifest_entries=(_entry("TSW_API_SYNC_PASSWORD"),),
                process_environment={"TSW_API_SYNC_PASSWORD": "api-value"},
            )

            sync.run()

            self.assertEqual(cli.ensured, [("tiny-swarm-world", "local")])
            self.assertIn("TSW_API_SYNC_PASSWORD", cli.values)

    def test_infisical_sync_failure_blocks_without_secret_value(self):
        fixed_value = operator_credential()
        sync = SecretSyncUseCase(
            store=InfisicalSecretStore(_FailingInfisicalCli()),
            storage=_STORAGE,
            manifest_entries=(_entry("TSW_FAILING_PASSWORD"),),
            process_environment={"TSW_FAILING_PASSWORD": fixed_value},
        )

        with self.assertRaises(SecretManagementBlocker) as raised:
            sync.run()

        self.assertIn("TSW_FAILING_PASSWORD", str(raised.exception))
        self.assertNotIn(fixed_value, str(raised.exception))

    def test_missing_required_external_secret_blocks(self):
        sync = InfisicalSecretSyncStep(
            cli=_FakeInfisicalCli(),
            storage=_STORAGE,
            manifest_entries=(
                SecretManifestEntry(
                    key="TSW_EXTERNAL_API_KEY",
                    service="external",
                    type="external_user_secret",
                    environment="local",
                    description="External API key",
                    source="external_user_secret",
                    required=True,
                ),
            ),
        )

        with self.assertRaises(SecretManagementBlocker):
            sync.run()

    def test_catalog_path_syncs_from_process_values_without_recovery_file(self):
        with tempfile.TemporaryDirectory():
            cli = _FakeInfisicalCli()
            sync = InfisicalSecretSyncStep(
                cli=cli,
                storage=_STORAGE,
                manifest_entries=(
                    _entry("TSW_INTERNAL_TEST_PASSWORD"),
                ),
                process_environment={"TSW_INTERNAL_TEST_PASSWORD": "from-installer"},
            )

            sync.run()

        self.assertEqual(cli.values["TSW_INTERNAL_TEST_PASSWORD"], "from-installer")
        self.assertEqual(sync.results[0]["sync_status"], "created")

    def test_internal_test_mode_prefers_existing_infisical_value_after_bootstrap(self):
        cli = _FakeInfisicalCli(existing={"TSW_INTERNAL_TEST_PASSWORD"})
        cli.values["TSW_INTERNAL_TEST_PASSWORD"] = "vault-value"
        sync = InfisicalSecretSyncStep(
            cli=cli,
            storage=_STORAGE,
            manifest_entries=(_entry("TSW_INTERNAL_TEST_PASSWORD"),),
            process_environment={"TSW_INTERNAL_TEST_PASSWORD": "operator-value"},
        )

        with self.assertRaisesRegex(SecretManagementBlocker, "Conflicting operator and secure values"):
            sync.run()

    def test_internal_test_honors_default_source_metadata_over_transport_value(self):
        cli = _FakeInfisicalCli()
        sync = InfisicalSecretSyncStep(
            cli=cli,
            storage=_STORAGE,
            manifest_entries=(_entry("TSW_PORTAINER_ADMIN_PASSWORD"),),
            process_environment={
                "TSW_PORTAINER_ADMIN_PASSWORD": "transport-value",
                "TSW_CREDENTIAL_SOURCE_MAP": (
                    '{"TSW_PORTAINER_ADMIN_PASSWORD":"default"}'
                ),
            },
        )

        sync.run()

        self.assertEqual(sync.results[0]["source"], "default")

    def test_internal_test_blocks_when_infisical_read_fails(self):
        sync = InfisicalSecretSyncStep(
            cli=_FailingReadInfisicalCli(),
            storage=_STORAGE,
            manifest_entries=(_entry("TSW_PORTAINER_ADMIN_PASSWORD"),),
            process_environment={"TSW_PORTAINER_ADMIN_PASSWORD": "operator-value"},
        )

        with self.assertRaisesRegex(SecretManagementBlocker, "reading key"):
            sync.run()

    def test_internal_test_full_manifest_keeps_external_refs_out_of_vault(self):
        entries = SecretManifestRenderer(
            _STORAGE,
            Path("infra/config/secrets/infisical-secrets.yaml"),
        ).run()
        external_keys = {
            "TSW_TRAEFIK_TLS_CERT_SECRET_NAME",
            "TSW_TRAEFIK_TLS_KEY_SECRET_NAME",
            "TSW_TRAEFIK_GUI_USERS_SECRET_NAME",
        }
        process_environment = {
            key: f"managed-{key.lower()}"
            for key in external_keys
        }
        cli = _FakeInfisicalCli()
        sync = InfisicalSecretSyncStep(
            cli=cli,
            storage=_STORAGE,
            manifest_entries=entries,
            process_environment=process_environment,
        )

        sync.run()

        self.assertTrue(external_keys.isdisjoint(cli.values))
        self.assertEqual(
            {
                result["key"]
                for result in sync.results
                if result["sync_status"] == "verified_external_reference"
            },
            external_keys,
        )

    def test_rendered_env_files_are_gitignored(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn("/.tiny-swarm/", gitignore)
        self.assertIn("*.local.env", gitignore)

    def test_secret_consumption_blocks_when_required_reference_is_missing(self):
        consumption = SecretConsumptionVerifier(
            manifest_entries=(_entry("TSW_REQUIRED_PASSWORD"),),
            stack_environment={},
        )

        consumption.run()
        result = consumption.verify()

        self.assertEqual(result.status.value, "blocked")
        self.assertEqual(result.evidence["missing_required_count"], "1")
        self.assertEqual(result.evidence["reason"], "required_consumer_missing")

    def test_secret_consumption_accepts_explicit_non_stack_consumer_reference(self):
        consumption = SecretConsumptionVerifier(
            manifest_entries=(_entry("TSW_REQUIRED_PASSWORD"),),
            stack_environment={},
            non_stack_consumer_refs={
                "TSW_REQUIRED_PASSWORD": "deployment:test-consumer",
            },
        )

        consumption.run()
        result = consumption.verify()

        self.assertEqual(result.status.value, "verified")
        self.assertEqual(result.evidence["missing_required_count"], "0")
        self.assertEqual(consumption.report[0]["consumer_status"], "configured")
        self.assertEqual(consumption.report[0]["consumer_ref"], "deployment:test-consumer")

    def test_secret_consumption_rejects_unknown_non_stack_consumer_reference(self):
        with self.assertRaisesRegex(ValueError, "Unknown managed config consumer key"):
            SecretConsumptionVerifier(
                manifest_entries=(_entry("TSW_REQUIRED_PASSWORD"),),
                non_stack_consumer_refs={
                    "TSW_UNKNOWN_PASSWORD": "deployment:test-consumer",
                },
            )

    def test_evidence_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            discovery = SecretDiscoveryStep(
                storage=_STORAGE,
                repo_root=root,
                manifest_entries=(_entry("TSW_POSTGRES_PASSWORD"),),
            )
            discovery.run()
            sync = InfisicalSecretSyncStep(
                cli=_FakeInfisicalCli(),
                storage=_STORAGE,
                manifest_entries=(_entry("TSW_POSTGRES_PASSWORD"),),
            )
            sync.run()
            consumption = SecretConsumptionVerifier(manifest_entries=(_entry("TSW_POSTGRES_PASSWORD"),), stack_environment={"postgres": {"TSW_POSTGRES_PASSWORD": operator_credential()}})
            consumption.run()
            writer = SecretEvidenceWriter(
                storage=_STORAGE,
                evidence_dir=root / "evidence",
                discovery=discovery,
                sync=sync,
                consumption=consumption,
            )

            writer.run()

            evidence = json.loads((root / "evidence" / "infisical-sync-result.json").read_text(encoding="utf-8"))
            self.assertIn("TSW_POSTGRES_PASSWORD", evidence["checked_secret_keys"])
            self.assertIn("TSW_POSTGRES_PASSWORD", evidence["synchronized_secret_keys"])
            self.assertNotIn("value", evidence["results"][0])
            self.assertNotIn(operator_credential(), (root / "evidence" / "secret-consumption-report.md").read_text(encoding="utf-8"))


def _entry(key: str) -> SecretManifestEntry:
    return SecretManifestEntry(
        key=key,
        service="service",
        type="managed_secret",
        environment="local",
        description="Catalog-backed managed secret",
        source="internal_test_catalog",
        required=True,
    )


def _write_repo_fixture(root: Path, file_name: str, content: str) -> Path:
    resolved_root = root.resolve(strict=True)
    destination = (resolved_root / file_name).resolve()
    if destination.parent != resolved_root or destination.name != file_name:
        raise ValueError("fixture destination must stay inside the temporary root")
    destination.write_text(content, encoding="utf-8")
    return destination


class _FakeInfisicalCli:
    def __init__(self, existing: set[str] | None = None, available: bool = True):
        self.existing = existing or set()
        self.available = available
        self.values: dict[str, str] = {}
        self.ensured: list[tuple[str, str]] = []
        self.reads: list[str] = []

    def is_available(self) -> bool:
        return self.available

    def run_bootstrap(self, args: tuple[str, ...]):
        raise AssertionError("not used")

    def ensure_project_environment(self, project: str, environment: str) -> None:
        self.ensured.append((project, environment))

    def secret_exists(self, key: str, *, project: str, environment: str) -> bool:
        return key in self.existing or key in self.values

    def get_secret(self, key: str, *, project: str, environment: str) -> str | None:
        self.reads.append(key)
        return self.values.get(key)

    def set_secret(self, key: str, value: str, *, project: str, environment: str) -> None:
        self.values[key] = value
        self.existing.add(key)


class _FailingInfisicalCli(_FakeInfisicalCli):
    def set_secret(self, key: str, value: str, *, project: str, environment: str) -> None:
        raise RuntimeError(f"sync failed for {key}")


class _FailingReadInfisicalCli(_FakeInfisicalCli):
    def get_secret(self, key: str, *, project: str, environment: str) -> str | None:
        raise RuntimeError(f"read failed for {key}")


if __name__ == "__main__":
    unittest.main()
