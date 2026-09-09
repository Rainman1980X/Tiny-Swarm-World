from __future__ import annotations

import base64
import hashlib
import hmac
import json
import unittest

from tiny_swarm_world.domain.configuration import (
    INTERNAL_TEST_PASSWORD,
    CredentialCatalog,
    CredentialCatalogError,
    CredentialConstraint,
    CredentialDefinition,
    CredentialType,
    default_configuration_contract,
    internal_test_catalog,
    internal_test_credential,
    internal_test_credentials,
    validate_internal_test_catalog,
    validate_internal_test_consumers,
)
from tiny_swarm_world.domain.configuration.configuration_contract import (
    validate_traefik_htpasswd,
)


class TestInternalTestCredentialCatalog(unittest.TestCase):
    def test_catalog_covers_required_contract_and_named_optional_components(self) -> None:
        catalog = internal_test_catalog()
        required_keys = {
            requirement.key
            for requirement in default_configuration_contract().requirements
            if requirement.required
        }
        required_keys.add("TSW_TRAEFIK_GUI_USERS_HTPASSWD")

        validate_internal_test_catalog()
        validate_internal_test_consumers(required_keys)

        self.assertTrue(required_keys <= set(catalog.by_key))
        self.assertIn("TSW_REDIS_PASSWORD", catalog.by_key)
        self.assertIn("TSW_GRAFANA_ADMIN_PASSWORD", catalog.by_key)
        self.assertIn("TSW_PROMETHEUS_BASIC_AUTH_PASSWORD", catalog.by_key)
        self.assertIn("TSW_REGISTRY_HTPASSWD", catalog.by_key)

    def test_every_definition_has_metadata_and_is_test_only(self) -> None:
        catalog = internal_test_catalog()

        self.assertEqual(20, len(catalog.definitions))
        for definition in catalog.definitions:
            with self.subTest(key=definition.key):
                self.assertTrue(definition.internal_test_only)
                self.assertTrue(definition.owner)
                self.assertTrue(definition.consumer)
                self.assertTrue(definition.derivation)
                self.assertIsInstance(definition.credential_type, CredentialType)
                self.assertTrue(definition.constraints.startup_semantics)
                self.assertIsNotNone(definition.constraints.charset)

    def test_compatible_human_passwords_use_canonical_value(self) -> None:
        catalog = internal_test_catalog().by_key
        compatible_keys = (
            "TSW_PORTAINER_ADMIN_PASSWORD",
            "TSW_NEXUS_ADMIN_PASSWORD",
            "TSW_JENKINS_ADMIN_PASSWORD",
            "TSW_PULSAR_MANAGER_ADMIN_PASSWORD",
            "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD",
            "TSW_POSTGRES_PASSWORD",
            "TSW_SONARQUBE_POSTGRES_PASSWORD",
            "TSW_INFISICAL_POSTGRES_PASSWORD",
            "TSW_INFISICAL_REDIS_PASSWORD",
        )

        for key in compatible_keys:
            with self.subTest(key=key):
                self.assertEqual(INTERNAL_TEST_PASSWORD, catalog[key].value)

        self.assertEqual(f"{INTERNAL_TEST_PASSWORD}!a", catalog["TSW_SONARQUBE_ADMIN_PASSWORD"].value)
        self.assertEqual(
            "admin@tiny-swarm-world.local",
            catalog["TSW_INFISICAL_LOGIN_EMAIL"].value,
        )

    def test_encoded_derivations_satisfy_their_consumer_formats(self) -> None:
        values = internal_test_credentials()
        signing_key = base64.b64decode(values["TSW_PULSAR_TOKEN_SECRET_KEY"], validate=True)
        self.assertEqual(32, len(signing_key))
        self.assertEqual(16, len(bytes.fromhex(values["TSW_INFISICAL_ENCRYPTION_KEY"])))
        self.assertEqual(32, len(bytes.fromhex(values["TSW_INFISICAL_AUTH_SECRET"])))
        validate_traefik_htpasswd(values["TSW_TRAEFIK_GUI_USERS_HTPASSWD"])

        header, payload, signature = values["TSW_PULSAR_ADMIN_TOKEN"].split(".")
        signing_input = f"{header}.{payload}".encode("ascii")
        expected = hmac.new(signing_key, signing_input, hashlib.sha256).digest()
        self.assertEqual(
            base64.urlsafe_b64encode(expected).decode("ascii").rstrip("="),
            signature,
        )
        decoded_payload = base64.urlsafe_b64decode(payload + "==")
        self.assertEqual({"sub": "admin"}, json.loads(decoded_payload))

    def test_resolution_is_deterministic_and_unknown_keys_fail_closed(self) -> None:
        self.assertEqual(internal_test_credentials(), internal_test_credentials())
        self.assertEqual(
            internal_test_credentials()["TSW_PULSAR_ADMIN_TOKEN"],
            internal_test_credential("TSW_PULSAR_ADMIN_TOKEN"),
        )
        with self.assertRaises(KeyError):
            internal_test_credential("TSW_UNKNOWN_PASSWORD")

        values = internal_test_credentials()
        with self.assertRaises(TypeError):
            values["TSW_NEW_PASSWORD"] = "invented"  # type: ignore[index]
        with self.assertRaises(TypeError):
            internal_test_catalog().by_key["TSW_NEW_PASSWORD"] = object()  # type: ignore[index]

    def test_safe_inventory_excludes_values(self) -> None:
        inventory = [definition.safe_dict() for definition in internal_test_catalog().definitions]
        serialized = repr(inventory)

        self.assertEqual(20, len(inventory))
        self.assertNotIn(INTERNAL_TEST_PASSWORD, serialized)
        self.assertNotIn(internal_test_credential("TSW_PULSAR_ADMIN_TOKEN"), serialized)
        self.assertEqual("human_password", inventory[0]["type"])

    def test_missing_active_consumer_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            CredentialCatalogError,
            "TSW_MISSING_PASSWORD",
        ):
            validate_internal_test_consumers(
                ("TSW_PORTAINER_ADMIN_PASSWORD", "TSW_MISSING_PASSWORD")
            )

        with self.assertRaisesRegex(CredentialCatalogError, "TSW_MISSING_PASSWORD"):
            CredentialCatalog(definitions=()).validate_consumers(("TSW_MISSING_PASSWORD",))

    def test_invalid_definition_metadata_fails_during_construction(self) -> None:
        valid_constraint = CredentialConstraint(startup_semantics="test")
        invalid_definitions = (
            lambda: CredentialDefinition(
                key="BAD_KEY",
                owner="test owner",
                consumer="test consumer",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=valid_constraint,
                derivation="test derivation",
            ),
            lambda: CredentialDefinition(
                key="TSW_EXAMPLE_PASSWORD",
                owner="",
                consumer="test consumer",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=valid_constraint,
                derivation="test derivation",
            ),
            lambda: CredentialDefinition(
                key="TSW_EXAMPLE_PASSWORD",
                owner="test owner",
                consumer="test consumer",
                credential_type="human_password",  # type: ignore[arg-type]
                value=INTERNAL_TEST_PASSWORD,
                constraints=valid_constraint,
                derivation="test derivation",
            ),
            lambda: CredentialDefinition(
                key="TSW_EXAMPLE_PASSWORD",
                owner="test owner",
                consumer="test consumer",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=valid_constraint,
                derivation="test derivation",
                internal_test_only=False,
            ),
        )
        for factory in invalid_definitions:
            with self.subTest(factory=factory), self.assertRaises(CredentialCatalogError):
                factory()

        with self.assertRaises(CredentialCatalogError):
            valid_definition = CredentialDefinition(
                key="TSW_EXAMPLE_PASSWORD",
                owner="test owner",
                consumer="test consumer",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=valid_constraint,
                derivation="test derivation",
            )
            CredentialCatalog(definitions=(valid_definition, valid_definition))
        with self.assertRaises(CredentialCatalogError):
            CredentialCatalog(definitions=(object(),))  # type: ignore[arg-type]

    def test_invalid_constraints_fail_early(self) -> None:
        invalid_constraints = (
            {"min_length": 0},
            {"max_length": 0},
            {"min_length": 4, "max_length": 3},
            {"fixed_byte_length": 0},
            {"entropy_bits": 0},
            {"charset": ""},
            {"encoding": "not-an-encoding"},
            {"decoded_format": "base32"},
            {"format_pattern": "["},
            {"startup_semantics": ""},
        )
        for kwargs in invalid_constraints:
            with self.subTest(kwargs=kwargs), self.assertRaises(CredentialCatalogError):
                CredentialConstraint(**kwargs)

    def test_constraint_validation_rejects_wrong_values(self) -> None:
        with self.assertRaisesRegex(CredentialCatalogError, "non-empty"):
            CredentialConstraint(startup_semantics="test").validate("")
        with self.assertRaisesRegex(CredentialCatalogError, "shorter"):
            CredentialConstraint(min_length=4, startup_semantics="test").validate("abc")
        with self.assertRaisesRegex(CredentialCatalogError, "exceeds"):
            CredentialConstraint(max_length=2, startup_semantics="test").validate("abc")
        with self.assertRaisesRegex(CredentialCatalogError, "fixed byte"):
            CredentialConstraint(fixed_byte_length=4, startup_semantics="test").validate("abc")
        with self.assertRaisesRegex(CredentialCatalogError, "format"):
            CredentialConstraint(
                format_pattern=r"[0-9]+",
                startup_semantics="test",
            ).validate("abc")
        with self.assertRaisesRegex(CredentialCatalogError, "encoding"):
            CredentialConstraint(encoding="ascii", startup_semantics="test").validate("é")
        with self.assertRaisesRegex(CredentialCatalogError, "encoded"):
            CredentialConstraint(
                fixed_byte_length=2,
                decoded_format="hex",
                startup_semantics="test",
            ).validate("not-hex")
        with self.assertRaisesRegex(CredentialCatalogError, "encoded"):
            CredentialConstraint(
                fixed_byte_length=2,
                decoded_format="base64",
                startup_semantics="test",
            ).validate("not base64!")


if __name__ == "__main__":
    unittest.main()
