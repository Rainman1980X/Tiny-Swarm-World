"""Offline regressions for credential acceptance; no service calls."""

import json
import unittest
from unittest.mock import MagicMock, patch

import requests

from tests.e2e.classic.authenticated_service_contract import probe_authentication


def response(status: int = 200, body: object = None, **headers: str) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    result.headers.update(headers)
    return result


class TestAuthenticatedServiceContract(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = patch("tests.e2e.classic.authenticated_service_contract.requests.Session").start()
        self.addCleanup(patch.stopall)
        self.invalid = MagicMock()
        self.valid = MagicMock()
        self.factory.side_effect = [self.invalid, self.valid]
        for session in (self.invalid, self.valid):
            session.__enter__.return_value = session

    def probe(self, route: str = "jenkins") -> dict[str, object]:
        return dict(probe_authentication(route, "https://service.test", "expected", "secret-fixture", "/ca.pem"))

    def test_basic_services_require_identity_and_invalid_rejection(self) -> None:
        for route, body in (("jenkins", {"authenticated": True, "name": "expected"}),
                            ("sonarqube", {"login": "expected", "isLoggedIn": True}),
                            ("nexus", [{"userId": "expected"}])):
            with self.subTest(route=route):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.get.return_value = response(401)
                self.valid.get.return_value = response(body=body)
                self.assertEqual(self.probe(route), {"authenticated_access_verified": True, "invalid_rejected": True,
                                                   "redacted_failure_reason": ""})
        self.assertFalse(self.valid.trust_env)
        self.assertEqual(self.valid.verify, "/ca.pem")
        self.assertFalse(self.valid.get.call_args.kwargs["allow_redirects"])

    def test_anonymous_http_200_never_verifies_identity(self) -> None:
        self.invalid.get.return_value = response(401)
        self.valid.get.return_value = response(body={"authenticated": False, "name": "expected"})
        self.assertEqual(self.probe()["redacted_failure_reason"], "identity_not_verified")

    def test_wrong_principal_never_verifies_identity(self) -> None:
        self.invalid.get.return_value = response(401)
        self.valid.get.return_value = response(body={"authenticated": True, "name": "other"})
        self.assertFalse(self.probe()["authenticated_access_verified"])

    def test_sonar_matching_name_without_logged_in_state_is_rejected(self) -> None:
        self.invalid.get.return_value = response(401)
        self.valid.get.return_value = response(body={"login": "expected", "isLoggedIn": False})
        self.assertFalse(self.probe("sonarqube")["authenticated_access_verified"])

    def test_infisical_400_requires_exact_invalid_login_schema(self) -> None:
        for message, rejected in (("Invalid username or email", True), ("Malformed request", False)):
            with self.subTest(message=message):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.post.return_value = response(400, {"message": message})
                self.valid.post.return_value = response(body={"accessToken": "fixture"})
                self.valid.get.return_value = response(body={"organizations": [{"id": "fixture"}]})
                self.assertEqual(self.probe("infisical")["invalid_rejected"], rejected)

    def test_invalid_credentials_accepted_never_pass(self) -> None:
        for session in (self.invalid, self.valid):
            session.get.return_value = response(body={"authenticated": True, "name": "expected"})
        self.assertEqual(self.probe()["redacted_failure_reason"], "invalid_credentials_not_rejected")
        self.invalid.get.assert_called_once()
        self.valid.get.assert_called_once()
        self.assertNotEqual(self.invalid.get.call_args.kwargs["auth"][1], "secret-fixture")

    def test_transport_failure_is_value_free_non_success(self) -> None:
        self.invalid.get.side_effect = requests.ConnectionError("secret-fixture https://private.test")
        result = self.probe()
        self.assertEqual(result["redacted_failure_reason"], "transport_failure")
        self.assertFalse(result["authenticated_access_verified"])
        self.assertFalse(result["invalid_rejected"])
        self.assertNotIn("secret-fixture", repr(result))
        self.valid.get.assert_not_called()

    def test_portainer_proves_principal_without_returning_token(self) -> None:
        self.invalid.post.return_value = response(403)
        self.valid.post.return_value = response(body={"jwt": "private-token-fixture"})
        self.valid.get.return_value = response(body={"Username": "expected"})
        result = self.probe("portainer")
        self.assertTrue(result["authenticated_access_verified"])
        self.assertTrue(result["invalid_rejected"])
        self.assertNotIn("private-token-fixture", repr(result))
        self.assertTrue(self.valid.get.call_args.args[0].endswith("/api/users/me"))

    def test_portainer_minted_token_is_not_invalid_rejection(self) -> None:
        for session in (self.invalid, self.valid):
            session.post.return_value = response(body={"jwt": "private-token-fixture"})
            session.get.return_value = response(403)
        self.assertFalse(self.probe("portainer")["invalid_rejected"])

    def test_portainer_422_requires_explicit_invalid_credentials(self) -> None:
        for message, rejected in (("Invalid credentials", True), ("Invalid request", False)):
            with self.subTest(message=message):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.post.return_value = response(422, {"message": message})
                self.valid.post.return_value = response(body={"jwt": "fixture"})
                self.valid.get.return_value = response(body={"Username": "expected"})
                self.assertEqual(self.probe("portainer")["invalid_rejected"], rejected)

    def test_redirect_server_error_and_malformed_body_do_not_pass(self) -> None:
        for status, body in ((302, {}), (500, {}), (200, []), (200, {"name": "expected"})):
            with self.subTest(status=status, body=body):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.get.return_value = response(401)
                self.valid.get.return_value = response(status, body)
                self.assertFalse(self.probe()["authenticated_access_verified"])

    def test_pulsar_requires_protected_read_after_identity_header(self) -> None:
        csrf = response()
        csrf._content = b"csrf-fixture"
        self.invalid.get.return_value = csrf
        self.valid.get.side_effect = [csrf, response(body={"total": 0, "data": []})]
        self.invalid.post.return_value = response(body={"error": "The user name or password not incorrect"})
        self.valid.post.return_value = response(body={"login": "success"}, username="expected", token="token-fixture")
        result = self.probe("pulsar-manager")
        self.assertTrue(result["authenticated_access_verified"])
        self.assertTrue(result["invalid_rejected"])
        self.assertNotIn("token-fixture", repr(result))
        self.assertTrue(self.valid.get.call_args.args[0].endswith("/pulsar-manager/environments"))

    def test_pulsar_login_success_without_identity_header_is_not_enough(self) -> None:
        self.invalid.get.return_value = self.valid.get.return_value = response(body="csrf-fixture")
        self.invalid.post.return_value = response(401)
        self.valid.post.return_value = response(body={"login": "success"})
        self.assertFalse(self.probe("pulsar-manager")["authenticated_access_verified"])
        self.valid.get.assert_called_once()

    def test_unknown_route_is_explicitly_unsupported_without_calls(self) -> None:
        self.assertEqual(self.probe("unknown")["redacted_failure_reason"], "unsupported_route")
        self.factory.assert_not_called()

    def test_pulsar_admin_requires_managed_token_for_protected_operation(self) -> None:
        self.invalid.get.return_value = response(401)
        self.valid.get.return_value = response(body=["configured-cluster"])
        result = self.probe("pulsar-admin-api")
        self.assertTrue(result["authenticated_access_verified"])
        self.assertTrue(result["invalid_rejected"])
        self.assertNotIn("secret-fixture", repr(result))
        self.assertTrue(self.valid.get.call_args.args[0].endswith("/admin/v2/clusters"))
        self.assertEqual(self.valid.get.call_args.kwargs["headers"], {"Authorization": "Bearer secret-fixture"})
        self.invalid.get.assert_called_once()
        self.valid.get.assert_called_once()

    def test_pulsar_admin_empty_or_malformed_clusters_are_not_evidence(self) -> None:
        body: object
        for body in ([], {}, [""], [" "], [1], [None]):
            with self.subTest(body=body):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.get.return_value = response(401)
                self.valid.get.return_value = response(body=body)
                self.assertFalse(self.probe("pulsar-admin-api")["authenticated_access_verified"])

    def test_pulsar_admin_invalid_token_accepted_is_not_a_pass(self) -> None:
        self.invalid.get.return_value = self.valid.get.return_value = response(body=["cluster"])
        self.assertEqual(self.probe("pulsar-admin-api")["redacted_failure_reason"],
                         "invalid_credentials_not_rejected")

    def test_infisical_requires_login_and_protected_organization_operation(self) -> None:
        self.invalid.post.return_value = response(401)
        self.valid.post.return_value = response(body={"accessToken": "private-token-fixture"})
        self.valid.get.return_value = response(body={"organizations": [{"id": "org-fixture"}]})
        result = self.probe("infisical")
        self.assertTrue(result["authenticated_access_verified"])
        self.assertTrue(result["invalid_rejected"])
        self.assertNotIn("private-token-fixture", repr(result))
        self.assertNotIn("org-fixture", repr(result))
        self.assertTrue(self.valid.get.call_args.args[0].endswith("/api/v1/organization"))
        self.invalid.post.assert_called_once()
        self.valid.post.assert_called_once()

    def test_infisical_accepted_login_with_forbidden_operation_is_not_rejection(self) -> None:
        for session in (self.invalid, self.valid):
            session.post.return_value = response(body={"accessToken": "private-token-fixture"})
            session.get.return_value = response(403)
        result = self.probe("infisical")
        self.assertFalse(result["authenticated_access_verified"])
        self.assertFalse(result["invalid_rejected"])

    def test_infisical_malformed_login_does_not_count_as_rejection(self) -> None:
        self.invalid.post.return_value = response(body={"error": "unspecified"})
        self.valid.post.return_value = response(401)
        self.assertFalse(self.probe("infisical")["invalid_rejected"])

    def test_infisical_missing_organization_is_not_evidence(self) -> None:
        body: object
        for body in ({}, [], {"organizations": []}, {"organizations": [{}]},
                     {"organizations": [{"id": 1}]}, {"organizations": [{"id": " "}]}):
            with self.subTest(body=body):
                self.factory.side_effect = [self.invalid, self.valid]
                self.invalid.post.return_value = response(401)
                self.valid.post.return_value = response(body={"accessToken": "private-token-fixture"})
                self.valid.get.return_value = response(body=body)
                self.assertFalse(self.probe("infisical")["authenticated_access_verified"])

    def test_url_credentials_are_rejected_without_calls(self) -> None:
        result = probe_authentication("jenkins", "https://user:secret-fixture@service.test", "u", "p")
        self.assertEqual(result["redacted_failure_reason"], "invalid_configuration")
        self.factory.assert_not_called()

    def test_malformed_url_is_value_free_configuration_failure(self) -> None:
        result = probe_authentication("jenkins", "https://[invalid", "u", "p")
        self.assertEqual(result["redacted_failure_reason"], "invalid_configuration")
        self.factory.assert_not_called()

    def test_malformed_json_is_not_authentication_evidence(self) -> None:
        self.invalid.get.return_value = response(401)
        malformed = response()
        malformed._content = b"private-token-fixture"
        self.valid.get.return_value = malformed
        result = self.probe()
        self.assertEqual(result["redacted_failure_reason"], "invalid_response")
        self.assertFalse(result["authenticated_access_verified"])
        self.assertNotIn("private-token-fixture", repr(result))
