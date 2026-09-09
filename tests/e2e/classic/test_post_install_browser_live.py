"""Opt-in live checks for completed Tiny Swarm World service access installs.

The default quality gate runs only static safety tests in this module. The
live checks run only with:

TSW_RUN_POST_INSTALL_BROWSER_LIVE=1 PYTHONPATH=src python3 -m unittest \
  tests.e2e.classic.test_post_install_browser_live

This is the canonical Classic post-install browser/API suite. It absorbs the
former integration runner's installed-surface and dashboard-route contract;
the former Playwright runner is not retained as a second browser framework.
"""

from __future__ import annotations

import json
import os
import requests
import socket
import ssl
import subprocess
import time
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, ClassVar
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from ruamel.yaml import YAML

from tiny_swarm_world.application.ports.repositories.port_effective_access_model_repository import (
    PortEffectiveAccessModelRepository,
)
from tiny_swarm_world.application.ports.port_tls_contract_resolver import (
    PortTlsContractResolver,
)
from tiny_swarm_world.domain.deployment import (
    ServiceStackProfile,
)
from tiny_swarm_world.domain.ingress import desired_https_ingress_for_profile
from tiny_swarm_world.infrastructure.adapters.repositories.port_registry_yaml_repository import (
    PortRegistryYamlRepository,
)
from tiny_swarm_world.infrastructure.adapters.ingress.local_tls_contract_resolver import (
    LocalTlsContractResolver,
    TlsContractConfigurationError,
)
from tiny_swarm_world.infrastructure.adapters.ingress.tls_state import (
    canonical_tls_state_root,
)
from tiny_swarm_world.infrastructure.composition_configuration import (
    DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
    DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
    TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
    TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
)
from tests.e2e.classic.browser_e2e_contract import (
    browser_route_expectations,
    live_browser_evidence_root,
)
from tools.live.secure_runtime_paths import ensure_secure_directory
from tests.support.effective_access_model_fixture import effective_access_model_fixture
from tests.support.sonar_safe_literals import sample_text, sample_url


RUN_LIVE_ENV = "TSW_RUN_POST_INSTALL_BROWSER_LIVE"
DEFAULT_ENV_FILE = Path(".tiny-swarm-world/local/live-installation.env")
MISSING_TEST_ENV_FILE = ".tiny-swarm-world/local/missing-live-installation.env"
MISSING_TEST_CA_BUNDLE = ".tiny-swarm-world/local/missing-ca-bundle.pem"
TEST_CA_BUNDLE = "/etc/ssl/certs/tiny-swarm-world-ca.pem"
DEFAULT_EVIDENCE_ROOT = Path(".tiny-swarm-world/evidence/classic-public-beta-rc1")
EVIDENCE_ROOT_ENV = "TSW_CLASSIC_EVIDENCE_ROOT"
SERVICE_ACCESS_DASHBOARD = Path("infra/config/compose/service-access/dashboard/index.html")
INFISICAL_SECRET_MANIFEST = Path("infra/config/secrets/infisical-secrets.yaml")
EXPECTED_INFISICAL_ITEMS = (
    "platform/portainer",
    "platform/nexus",
    "platform/jenkins",
    "platform/pulsar",
    "platform/pulsar-manager",
    "platform/sonarqube",
    "platform/infisical",
)
EXPECTED_INFISICAL_ITEM_KEYS = {
    "platform/jenkins": "TSW_JENKINS_ADMIN_PASSWORD",
    "platform/nexus": "TSW_NEXUS_ADMIN_PASSWORD",
    "platform/portainer": "TSW_PORTAINER_ADMIN_PASSWORD",
    "platform/pulsar": "TSW_PULSAR_ADMIN_TOKEN",
    "platform/pulsar-manager": "TSW_PULSAR_MANAGER_ADMIN_PASSWORD",
    "platform/sonarqube": "TSW_SONARQUBE_ADMIN_PASSWORD",
    "platform/infisical": "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD",
}
NO_LOGIN_SERVICES = ("service-access", "swagger")
SERVICE_ALLOWED_STATUSES = {
    "jenkins": (200, 403),
    "nexus-docker-registry": (401,),
    "pulsar-admin-api": (200, 401, 403),
}
DASHBOARD_REDIRECT_STATUSES = (301, 302, 303, 307, 308)
FORBIDDEN_EVIDENCE_FRAGMENTS = (
    "authorization",
    "bearer ",
    "password",
    "secret",
    "token",
    "TSW_",
    "userinfo",
)
MANAGED_CREDENTIAL_KEY_SUFFIXES = ("HTPASSWD", "PASSWORD", "TOKEN")


@dataclass(frozen=True)
class ServiceCheck:
    name: str
    url: str
    follow_redirects: bool = True
    allowed_statuses: tuple[int, ...] = (200,)


@dataclass(frozen=True)
class HttpProbeResult:
    service: str
    url: str
    reachable: bool
    status_code: int | None
    content_type: str
    result: str
    redacted_failure_reason: str = ""

    def to_evidence(self) -> dict[str, object]:
        return {
            "content_type": self.content_type,
            "reachable": self.reachable,
            "redacted_failure_reason": self.redacted_failure_reason,
            "result": self.result,
            "service": self.service,
            "status_code": self.status_code,
            "url": self.url,
        }


@dataclass(frozen=True)
class ReadinessSummary:
    attempts: int
    duration_seconds: float
    pending_services: tuple[str, ...]

    def to_evidence(self) -> dict[str, object]:
        return {
            "attempts": self.attempts,
            "duration_seconds": round(self.duration_seconds, 3),
            "pending_services": list(self.pending_services),
            "result": "passed" if not self.pending_services else "failed",
        }


class ReadinessDeadlineExceeded(AssertionError):
    def __init__(
        self,
        summary: ReadinessSummary,
        results: tuple[HttpProbeResult, ...],
    ) -> None:
        self.summary = summary
        self.results = results
        super().__init__(
            "post_install_browser_readiness_timeout: pending="
            + ",".join(summary.pending_services)
        )


@dataclass(frozen=True)
class HttpsRouteProbeResult:
    service: str
    hostname: str
    reachable: bool
    status_code: int | None
    tls_status: str
    result: str
    redacted_failure_reason: str = ""

    def to_evidence(self) -> dict[str, object]:
        return {
            "hostname": self.hostname,
            "reachable": self.reachable,
            "redacted_failure_reason": self.redacted_failure_reason,
            "result": self.result,
            "service": self.service,
            "status_code": self.status_code,
            "tls_status": self.tls_status,
        }


@dataclass(frozen=True)
class LivePostInstallConfig:
    dashboard_url: str
    ingress_base_domain: str
    infisical_url: str
    infisical_email: str | None
    infisical_password: str | None
    pulsar_admin_url: str
    pulsar_admin_token: str | None
    pulsar_manager_url: str
    pulsar_manager_password: str | None
    sonarqube_url: str
    sonarqube_username: str
    sonarqube_password: str | None
    timeout_seconds: float
    tls_ca_bundle: str | None

    @classmethod
    def from_environment(
        cls,
        tls_contract_resolver: PortTlsContractResolver | None = None,
    ) -> "LivePostInstallConfig":
        local_env = _load_shell_environment(
            Path(os.environ.get("TSW_LIVE_INSTALLATION_ENV", DEFAULT_ENV_FILE))
        )
        dashboard_url = _env_value(local_env, "TSW_DASHBOARD_URL", "http://localhost:10000")
        ingress_base_domain = _env_value(
            local_env,
            "TSW_INGRESS_BASE_DOMAIN",
            "tsw.local",
        )
        infisical_url = _env_value(local_env, "TSW_INFISICAL_URL", "http://localhost:17080")
        pulsar_admin_url = _env_value(local_env, "TSW_PULSAR_PUBLIC_ADMIN_URL", "http://localhost:14080")
        pulsar_manager_url = _env_value(
            local_env,
            "TSW_PULSAR_MANAGER_URL",
            "http://localhost:14081",
        )
        sonarqube_url = _env_value(local_env, "TSW_SONARQUBE_URL", "http://localhost:12000")
        return cls(
            dashboard_url=_validated_local_url(dashboard_url, "dashboard"),
            ingress_base_domain=_validated_ingress_base_domain(ingress_base_domain),
            infisical_url=_validated_local_url(infisical_url, "infisical"),
            infisical_email=_env_optional(local_env, "TSW_INFISICAL_LOGIN_EMAIL"),
            infisical_password=_env_optional(
                local_env,
                "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD",
            ),
            pulsar_admin_url=_validated_local_url(pulsar_admin_url, "pulsar"),
            pulsar_admin_token=_env_optional(local_env, "TSW_PULSAR_ADMIN_TOKEN"),
            pulsar_manager_url=_validated_local_url(pulsar_manager_url, "pulsar_manager"),
            pulsar_manager_password=_env_optional(
                local_env,
                "TSW_PULSAR_MANAGER_ADMIN_PASSWORD",
            ),
            sonarqube_url=_validated_local_url(sonarqube_url, "sonarqube"),
            sonarqube_username=_env_value(local_env, "TSW_SONARQUBE_ADMIN_USERNAME", "admin"),
            sonarqube_password=_env_optional(local_env, "TSW_SONARQUBE_ADMIN_PASSWORD"),
            timeout_seconds=float(os.environ.get("TSW_POST_INSTALL_BROWSER_TIMEOUT", "45")),
            tls_ca_bundle=_canonical_live_trust_bundle(
                tls_contract_resolver
                or _canonical_tls_contract_resolver({**local_env, **os.environ})
            ),
        )


class StaticPostInstallLiveSuiteTest(unittest.TestCase):
    def test_dashboard_declares_expected_infisical_item_references(self) -> None:
        references = _dashboard_references(SERVICE_ACCESS_DASHBOARD)

        self.assertEqual(EXPECTED_INFISICAL_ITEMS, references.credential_items)
        for service in NO_LOGIN_SERVICES:
            with self.subTest(service=service):
                self.assertIn(service, references.no_login_services)

    def test_live_service_checks_are_safe_routed_urls(self) -> None:
        checks = _service_checks("http://localhost")
        expectations = browser_route_expectations()

        self.assertEqual(len(expectations) + 1, len(checks))
        for check in checks:
            with self.subTest(service=check.name):
                parsed = urlparse(check.url)
                self.assertIn(parsed.scheme, {"http", "https"})
                self.assertIn(parsed.hostname, {"localhost"} | _routed_hostnames())
                self.assertFalse(parsed.username)
                self.assertFalse(parsed.password)
                self.assertFalse(parsed.query)
                self.assertFalse(parsed.fragment)

    def test_live_service_checks_use_preferred_routed_ports(self) -> None:
        checks = _service_checks("http://localhost")
        ports_by_name = {check.name: urlparse(check.url).port for check in checks}

        self.assertIsNone(ports_by_name["service-access"])
        for expectation in browser_route_expectations():
            self.assertIsNone(
                ports_by_name[f"service-access-route:{expectation.route_name}"]
            )

    def test_live_service_checks_use_explicit_browser_status_allowlists(self) -> None:
        checks = _service_checks("http://localhost")

        for check in checks:
            with self.subTest(service=check.name):
                self.assertNotIn(404, check.allowed_statuses)
                self.assertTrue(check.allowed_statuses)
                self.assertTrue(
                    all(100 <= status <= 499 for status in check.allowed_statuses)
                )

    def test_routed_service_checks_accept_safe_redirects_without_following_them(self) -> None:
        checks = _service_checks("http://localhost")

        for check in checks:
            if not check.name.startswith("service-access-route:"):
                continue
            with self.subTest(service=check.name):
                self.assertFalse(check.follow_redirects)
                self.assertTrue(
                    set(DASHBOARD_REDIRECT_STATUSES).issubset(check.allowed_statuses)
                )

    def test_https_route_checks_use_tsw_local_https_hostnames(self) -> None:
        checks = _https_route_checks("tsw.local")
        expectations = browser_route_expectations()

        self.assertEqual(
            tuple(expectation.route_name for expectation in expectations),
            tuple(check.name for check in checks),
        )
        self.assertEqual(
            tuple(expectation.dashboard_url for expectation in expectations),
            tuple(check.url for check in checks),
        )
        for check in checks:
            with self.subTest(service=check.name):
                parsed = urlparse(check.url)
                self.assertEqual(parsed.scheme, "https")
                self.assertIsNone(parsed.port)
                self.assertIsNotNone(parsed.hostname)
                self.assertTrue(parsed.hostname and parsed.hostname.endswith(".tsw.local"))
                self.assertFalse(parsed.username)
                self.assertFalse(parsed.password)
                self.assertFalse(parsed.query)
                self.assertFalse(parsed.fragment)

    def test_enabled_optional_routes_enter_post_install_check_matrix(self) -> None:
        with effective_access_model_fixture(
            enabled_services=("prometheus", "grafana", "tiny-swarm")
        ) as fixture:
            checks = _service_checks(
                "http://localhost",
                model_repository=fixture.repository,
            )
            https_checks = _https_route_checks(
                "tsw.local",
                model_repository=fixture.repository,
            )

        service_check_names = {check.name for check in checks}
        https_check_names = {check.name for check in https_checks}
        for route_name in ("prometheus", "grafana", "app", "api"):
            with self.subTest(route=route_name):
                self.assertIn(f"service-access-route:{route_name}", service_check_names)
                self.assertIn(route_name, https_check_names)

    def test_https_route_matrix_evidence_is_redacted_and_actionable(self) -> None:
        result = HttpsRouteProbeResult(
            service="jenkins",
            hostname="jenkins.tsw.local",
            reachable=False,
            status_code=None,
            tls_status="blocked_hostname_resolution",
            result="blocked",
            redacted_failure_reason="hostname_unresolved",
        )

        evidence = result.to_evidence()

        self.assertTrue(_evidence_safe(evidence))
        self.assertEqual(evidence["service"], "jenkins")
        self.assertEqual(evidence["hostname"], "jenkins.tsw.local")
        self.assertEqual(evidence["tls_status"], "blocked_hostname_resolution")
        self.assertNotIn("url", evidence)

    def test_live_evidence_root_uses_classic_rc1_target(self) -> None:
        self.assertEqual(
            DEFAULT_EVIDENCE_ROOT.as_posix(),
            ".tiny-swarm-world/evidence/classic-public-beta-rc1",
        )

    def test_live_config_rejects_non_local_operator_urls(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE,
                "TSW_DASHBOARD_URL": "https://example.invalid",
            },
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "post_install_browser_setup_blocker: invalid_local_dashboard_url",
            ):
                LivePostInstallConfig.from_environment()

    def test_live_config_rejects_invalid_ingress_base_domains(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE,
                "TSW_INGRESS_BASE_DOMAIN": "localhost",
            },
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "post_install_browser_setup_blocker: invalid_ingress_base_domain",
            ):
                LivePostInstallConfig.from_environment()

    def test_live_config_rejects_secret_bearing_infisical_urls(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE,
                "TSW_DASHBOARD_URL": "http://localhost:10000",
                "TSW_INFISICAL_URL": sample_url("https", "user:credential", "localhost"),
            },
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "infisical_setup_blocker: invalid_local_infisical_url",
            ):
                LivePostInstallConfig.from_environment()

    def test_live_config_accepts_operator_ca_bundle_path(self) -> None:
        resolver = Mock()
        resolver.resolve.return_value.trust_bundle = Path(TEST_CA_BUNDLE)
        with (
            patch.dict(
                os.environ,
                {
                    "TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE,
                    "TSW_LIVE_TLS_CA_BUNDLE": TEST_CA_BUNDLE,
                },
            ),
            patch.object(Path, "is_file", return_value=True),
        ):
            config = LivePostInstallConfig.from_environment(resolver)

        self.assertEqual(config.tls_ca_bundle, TEST_CA_BUNDLE)

    def test_live_config_rejects_missing_operator_ca_bundle(self) -> None:
        resolver = Mock()
        resolver.resolve.side_effect = TlsContractConfigurationError(
            "TLS material is missing"
        )
        with (
            patch.dict(
                os.environ,
                {
                    "TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE,
                    "TSW_LIVE_TLS_CA_BUNDLE": MISSING_TEST_CA_BUNDLE,
                },
            ),
            patch.object(Path, "is_file", return_value=False),
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "post_install_browser_setup_blocker: invalid_tls_ca_bundle",
            ):
                LivePostInstallConfig.from_environment(resolver)

    def test_live_config_uses_canonical_resolver_trust_bundle(self) -> None:
        resolver = Mock()
        resolver.resolve.return_value.trust_bundle = Path(TEST_CA_BUNDLE)

        with (
            patch.dict(
                os.environ,
                {"TSW_LIVE_INSTALLATION_ENV": MISSING_TEST_ENV_FILE},
            ),
            patch.object(Path, "is_file", return_value=True),
        ):
            config = LivePostInstallConfig.from_environment(resolver)

        self.assertEqual(config.tls_ca_bundle, TEST_CA_BUNDLE)
        resolver.resolve.assert_called_once_with()

    def test_http_probe_passes_operator_ca_bundle_to_https_request(self) -> None:
        check = ServiceCheck("service-access", "https://service-access.tsw.local/")

        with patch(
            f"{__name__}._http_head_or_get",
            return_value=(200, "text/html"),
        ) as request:
            result = _probe_http(
                check,
                5.0,
                tls_ca_bundle=TEST_CA_BUNDLE,
            )

        self.assertTrue(result.reachable)
        request.assert_called_once_with(
            check.url,
            5.0,
            follow_redirects=True,
            tls_ca_bundle=TEST_CA_BUNDLE,
        )

    def test_http_probe_retries_get_when_head_is_not_browser_relevant(self) -> None:
        class _Response:
            status = 200
            headers = {"content-type": "text/html"}

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        opener = Mock()
        headers = Message()
        headers["content-type"] = "text/html"
        opener.open.side_effect = (
            HTTPError(
                "https://swagger.tsw.local/",
                404,
                "not found",
                headers,
                None,
            ),
            _Response(),
        )

        with patch(f"{__name__}.build_opener", return_value=opener):
            status_code, content_type = _http_head_or_get(
                "https://swagger.tsw.local/",
                5.0,
                follow_redirects=True,
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(content_type, "text/html")
        self.assertEqual(
            [call.args[0].get_method() for call in opener.open.call_args_list],
            ["HEAD", "GET"],
        )

    def test_readiness_returns_immediately_when_all_services_are_ready(self) -> None:
        clock = _FakeMonotonicClock()
        checks = (ServiceCheck("dashboard", "https://dashboard.tsw.local"),)
        probe = Mock(return_value=_ready_probe_result(checks[0]))

        results, summary = _wait_for_service_readiness(
            checks,
            10.0,
            tls_ca_bundle=TEST_CA_BUNDLE,
            probe=probe,
            monotonic=clock,
            sleep=clock.sleep,
        )

        self.assertTrue(results[0].reachable)
        self.assertEqual(summary.attempts, 1)
        self.assertEqual(summary.pending_services, ())
        probe.assert_called_once_with(
            checks[0],
            5.0,
            tls_ca_bundle=TEST_CA_BUNDLE,
        )

    def test_readiness_retries_pending_service_until_it_is_ready(self) -> None:
        clock = _FakeMonotonicClock()
        check = ServiceCheck("dashboard", "https://dashboard.tsw.local")
        probe = Mock(
            side_effect=(
                _failed_probe_result(check, "connection_error"),
                _ready_probe_result(check),
            )
        )

        _results, summary = _wait_for_service_readiness(
            (check,),
            10.0,
            probe=probe,
            monotonic=clock,
            sleep=clock.sleep,
            retry_interval_seconds=1.0,
        )

        self.assertEqual(summary.attempts, 2)
        self.assertEqual(summary.duration_seconds, 1.0)

    def test_readiness_caps_each_probe_by_remaining_global_deadline(self) -> None:
        clock = _FakeMonotonicClock()
        checks = (
            ServiceCheck("dashboard", "https://dashboard.tsw.local"),
            ServiceCheck("jenkins", "https://jenkins.tsw.local"),
        )
        observed_timeouts: list[float] = []

        def probe(
            check: ServiceCheck,
            timeout_seconds: float,
            **_kwargs: object,
        ) -> HttpProbeResult:
            observed_timeouts.append(timeout_seconds)
            if check is checks[0]:
                clock.current += 4.0
            return _ready_probe_result(check)

        _wait_for_service_readiness(
            checks,
            6.0,
            per_probe_timeout_seconds=5.0,
            probe=probe,
            monotonic=clock,
            sleep=clock.sleep,
        )

        self.assertEqual(observed_timeouts, [5.0, 2.0])

    def test_readiness_rejects_ready_result_returned_after_global_deadline(self) -> None:
        clock = _FakeMonotonicClock()
        check = ServiceCheck("dashboard", "https://dashboard.tsw.local")

        def late_ready_probe(
            selected_check: ServiceCheck,
            _timeout_seconds: float,
            **_kwargs: object,
        ) -> HttpProbeResult:
            clock.current = 2.1
            return _ready_probe_result(selected_check)

        with self.assertRaises(ReadinessDeadlineExceeded) as raised:
            _wait_for_service_readiness(
                (check,),
                2.0,
                probe=late_ready_probe,
                monotonic=clock,
                sleep=clock.sleep,
            )

        self.assertEqual(raised.exception.summary.pending_services, ("dashboard",))
        self.assertEqual(raised.exception.results[0].result, "failed")
        self.assertEqual(
            raised.exception.results[0].redacted_failure_reason,
            "global_deadline_exceeded",
        )

    def test_readiness_empty_check_matrix_is_immediate_success(self) -> None:
        clock = _FakeMonotonicClock()

        results, summary = _wait_for_service_readiness(
            (),
            2.0,
            monotonic=clock,
            sleep=clock.sleep,
        )

        self.assertEqual(results, ())
        self.assertEqual(summary, ReadinessSummary(0, 0.0, ()))

    def test_readiness_global_timeout_is_a_failure_with_redacted_summary(self) -> None:
        clock = _FakeMonotonicClock()
        check = ServiceCheck("dashboard", "https://dashboard.tsw.local")

        with self.assertRaises(ReadinessDeadlineExceeded) as raised:
            _wait_for_service_readiness(
                (check,),
                2.0,
                probe=Mock(return_value=_failed_probe_result(check, "connection_error")),
                monotonic=clock,
                sleep=clock.sleep,
                retry_interval_seconds=1.0,
            )

        self.assertEqual(raised.exception.summary.pending_services, ("dashboard",))
        self.assertEqual(raised.exception.summary.duration_seconds, 2.0)
        self.assertGreaterEqual(raised.exception.summary.attempts, 1)
        self.assertTrue(_evidence_safe(raised.exception.summary.to_evidence()))

    def test_readiness_probe_exception_is_redacted_and_remains_failure(self) -> None:
        clock = _FakeMonotonicClock()
        check = ServiceCheck("dashboard", "https://dashboard.tsw.local")

        with self.assertRaises(ReadinessDeadlineExceeded) as raised:
            _wait_for_service_readiness(
                (check,),
                1.0,
                probe=Mock(side_effect=RuntimeError("credential=do-not-record")),
                monotonic=clock,
                sleep=clock.sleep,
            )

        self.assertEqual(
            raised.exception.results[0].redacted_failure_reason,
            "probe_exception_RuntimeError",
        )
        self.assertNotIn("do-not-record", str(raised.exception))

    def test_readiness_tls_failure_never_becomes_skip_or_success(self) -> None:
        clock = _FakeMonotonicClock()
        check = ServiceCheck("dashboard", "https://dashboard.tsw.local")

        with self.assertRaises(ReadinessDeadlineExceeded) as raised:
            _wait_for_service_readiness(
                (check,),
                1.0,
                probe=Mock(return_value=_failed_probe_result(check, "SSLCertVerificationError")),
                monotonic=clock,
                sleep=clock.sleep,
            )

        self.assertEqual(raised.exception.results[0].result, "failed")
        self.assertEqual(
            raised.exception.results[0].redacted_failure_reason,
            "SSLCertVerificationError",
        )

    def test_redacted_evidence_rejects_secret_like_keys_and_values(self) -> None:
        unsafe = {
            "service": "jenkins",
            sample_text("pass", "word"): "value",
            "redacted_failure_reason": "token leaked",
        }

        self.assertFalse(_evidence_safe(unsafe))

    def test_infisical_inventory_evidence_contains_item_names_only(self) -> None:
        evidence = _infisical_item_evidence(
            expected_item="platform/jenkins",
            item_present=False,
            result="blocked",
            redacted_failure_reason="missing_login_material",
        )

        self.assertTrue(_evidence_safe(evidence))
        self.assertEqual(evidence["expected_infisical_item"], "platform/jenkins")
        self.assertNotIn("value", evidence)

    def test_infisical_managed_password_manifest_keys_are_discoverable(self) -> None:
        expected_keys = _expected_infisical_password_keys()

        self.assertIn("TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD", expected_keys)
        self.assertIn("TSW_JENKINS_ADMIN_PASSWORD", expected_keys)
        self.assertIn("TSW_NEXUS_ADMIN_PASSWORD", expected_keys)
        self.assertIn("TSW_PORTAINER_ADMIN_PASSWORD", expected_keys)
        self.assertIn("TSW_PULSAR_ADMIN_TOKEN", expected_keys)
        self.assertNotIn("TSW_INFISICAL_BOOTSTRAP_TOKEN", expected_keys)
        self.assertTrue(all(key.endswith(MANAGED_CREDENTIAL_KEY_SUFFIXES) for key in expected_keys))

    def test_traefik_tls_secret_name_manifest_entries_are_value_free(self) -> None:
        manifest = INFISICAL_SECRET_MANIFEST.read_text(encoding="utf-8")

        self.assertIn("- key: TSW_TRAEFIK_TLS_CERT_SECRET_NAME", manifest)
        self.assertIn("- key: TSW_TRAEFIK_TLS_KEY_SECRET_NAME", manifest)
        self.assertIn("- key: TSW_TRAEFIK_GUI_USERS_SECRET_NAME", manifest)
        self.assertIn("source: external_user_secret", manifest)
        self.assertNotIn("-----BEGIN", manifest)
        self.assertNotIn("PRIVATE KEY", manifest)


@unittest.skipUnless(
    os.environ.get(RUN_LIVE_ENV) == "1",
    f"set {RUN_LIVE_ENV}=1 to run post-install live browser checks",
)
class PostInstallBrowserLiveTest(unittest.TestCase):
    config: ClassVar[LivePostInstallConfig]
    evidence: ClassVar[_EvidenceRecorder]

    @classmethod
    def setUpClass(cls) -> None:
        root = live_browser_evidence_root()
        cls.config = LivePostInstallConfig.from_environment()
        cls.evidence = _EvidenceRecorder(root)

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "evidence"):
            cls.evidence.write()

    def test_01_service_routes_return_browser_relevant_http_responses(self) -> None:
        try:
            results, summary = _wait_for_service_readiness(
                _service_checks(self.config.dashboard_url),
                self.config.timeout_seconds,
                tls_ca_bundle=self.config.tls_ca_bundle,
            )
        except ReadinessDeadlineExceeded as exc:
            for result in exc.results:
                self.evidence.record("service", result.to_evidence())
            self.evidence.record("service_readiness", exc.summary.to_evidence())
            raise AssertionError(
                f"{exc}; evidence={self.evidence.path.as_posix()}"
            ) from None

        for result in results:
            self.evidence.record("service", result.to_evidence())
        self.evidence.record("service_readiness", summary.to_evidence())

    def test_02_https_ingress_hostnames_resolve(self) -> None:
        unresolved: list[str] = []
        for check in _https_route_checks(self.config.ingress_base_domain):
            hostname = _hostname_for_check(check)
            with self.subTest(service=check.name, hostname=hostname):
                resolved = _hostname_resolves(hostname)
                self.evidence.record(
                    "hostname_resolution",
                    _hostname_resolution_evidence(
                        service=check.name,
                        hostname=hostname,
                        resolved=resolved,
                    ),
                )
                if not resolved:
                    unresolved.append(hostname)

        if unresolved:
            raise AssertionError(
                "post_install_browser_hostname_resolution_blocked: "
                f"{','.join(unresolved)}; evidence={self.evidence.path.as_posix()}"
            )

    def test_03_https_ingress_routes_return_browser_relevant_responses(self) -> None:
        failures: list[HttpsRouteProbeResult] = []
        for check in _https_route_checks(self.config.ingress_base_domain):
            hostname = _hostname_for_check(check)
            with self.subTest(service=check.name, hostname=hostname):
                result = _probe_https_route(
                    check,
                    self.config.timeout_seconds,
                    tls_ca_bundle=self.config.tls_ca_bundle,
                )
                self.evidence.record("https_route", result.to_evidence())
                if not result.reachable:
                    failures.append(result)

        if failures:
            failed_services = ",".join(result.service for result in failures)
            raise AssertionError(
                "post_install_browser_https_route_failed: "
                f"{failed_services}; evidence={self.evidence.path.as_posix()}"
            )

    def test_04_infisical_contains_required_credential_items(self) -> None:
        missing_material = _missing_infisical_login_material(self.config)
        if missing_material:
            for item in EXPECTED_INFISICAL_ITEMS:
                self.evidence.record(
                    "infisical_item",
                    _infisical_item_evidence(
                        expected_item=item,
                        item_present=False,
                        result="blocked",
                        redacted_failure_reason="missing_login_material",
                    ),
                )
            raise AssertionError(
                "infisical_setup_blocker: missing "
                f"{','.join(missing_material)}; evidence={self.evidence.path.as_posix()}"
            )

        missing_items = _missing_infisical_items(self.config)
        for item in EXPECTED_INFISICAL_ITEMS:
            self.evidence.record(
                "infisical_item",
                _infisical_item_evidence(
                    expected_item=item,
                    item_present=item not in missing_items,
                    result="passed" if item not in missing_items else "failed",
                    redacted_failure_reason=(
                        "" if item not in missing_items else "expected_item_not_visible"
                    ),
                ),
            )

        if missing_items:
            raise AssertionError(
                "infisical_credential_inventory_missing: "
                f"{','.join(missing_items)}; evidence={self.evidence.path.as_posix()}"
            )

    def test_05_infisical_secret_management_is_bootstrapped(self) -> None:
        missing_material = _missing_infisical_login_material(self.config)
        if missing_material:
            self.evidence.record(
                "infisical_management",
                _infisical_management_evidence(
                    result="blocked",
                    installed=False,
                    super_admin_present=False,
                    project_present=False,
                    expected_credential_count=0,
                    present_credential_count=0,
                    redacted_failure_reason="missing_login_material",
                ),
            )
            raise AssertionError(
                "infisical_setup_blocker: missing "
                f"{','.join(missing_material)}; evidence={self.evidence.path.as_posix()}"
            )

        expected_password_keys = _expected_infisical_password_keys()
        status = _infisical_management_status(
            self.config,
            expected_password_keys,
        )
        self.evidence.record(
            "infisical_management",
            _infisical_management_evidence(
                result="passed" if status.passed else "failed",
                installed=status.installed,
                super_admin_present=status.super_admin_present,
                project_present=status.project_present,
                expected_credential_count=len(expected_password_keys),
                present_credential_count=status.present_password_count,
                redacted_failure_reason=status.redacted_failure_reason,
            ),
        )

        if not status.passed:
            raise AssertionError(
                "infisical_secret_management_incomplete: "
                f"{status.redacted_failure_reason}; evidence={self.evidence.path.as_posix()}"
            )

    def test_06_sonarqube_admin_credential_is_configured(self) -> None:
        if not self.config.sonarqube_password:
            self.evidence.record(
                "sonarqube_management",
                _sonarqube_management_evidence(
                    result="blocked",
                    configured_login_valid=False,
                    default_login_disabled=False,
                    redacted_failure_reason="missing_login_material",
                ),
            )
            raise AssertionError(
                "sonarqube_setup_blocker: missing_login_material; "
                f"evidence={self.evidence.path.as_posix()}"
            )

        configured_valid = _sonarqube_auth_valid(
            self.config.sonarqube_url,
            self.config.sonarqube_username,
            self.config.sonarqube_password,
            self.config.timeout_seconds,
        )
        default_valid = _sonarqube_auth_valid(
            self.config.sonarqube_url,
            "admin",
            "admin",
            self.config.timeout_seconds,
        )
        self.evidence.record(
            "sonarqube_management",
            _sonarqube_management_evidence(
                result="passed" if configured_valid and not default_valid else "failed",
                configured_login_valid=configured_valid,
                default_login_disabled=not default_valid,
                redacted_failure_reason=(
                    "" if configured_valid and not default_valid else "managed_login_inactive"
                ),
            ),
        )
        if not configured_valid or default_valid:
            raise AssertionError(
                "sonarqube_managed_credential_incomplete: "
                f"evidence={self.evidence.path.as_posix()}"
            )

    def test_07_pulsar_admin_api_requires_and_accepts_configured_token(self) -> None:
        if not self.config.pulsar_admin_token:
            self.evidence.record(
                "pulsar_management",
                _pulsar_management_evidence(
                    result="blocked",
                    unauthenticated_rejected=False,
                    configured_login_valid=False,
                    redacted_failure_reason="missing_login_material",
                ),
            )
            raise AssertionError(
                "pulsar_setup_blocker: missing_login_material; "
                f"evidence={self.evidence.path.as_posix()}"
            )

        status = _pulsar_admin_auth_status(
            self.config.pulsar_admin_url,
            self.config.pulsar_admin_token,
            self.config.timeout_seconds,
        )
        self.evidence.record(
            "pulsar_management",
            _pulsar_management_evidence(
                result="passed" if status["passed"] else "failed",
                unauthenticated_rejected=bool(status["unauthenticated_rejected"]),
                configured_login_valid=bool(status["configured_login_valid"]),
                redacted_failure_reason=str(status["redacted_failure_reason"]),
            ),
        )
        if not status["passed"]:
            raise AssertionError(
                "pulsar_managed_credential_incomplete: "
                f"{status['redacted_failure_reason']}; evidence={self.evidence.path.as_posix()}"
            )

    def test_08_pulsar_manager_admin_login_is_configured(self) -> None:
        if not self.config.pulsar_manager_password:
            self.evidence.record(
                "pulsar_manager_management",
                _pulsar_manager_management_evidence(
                    result="blocked",
                    csrf_available=False,
                    configured_login_valid=False,
                    redacted_failure_reason="missing_login_material",
                ),
            )
            raise AssertionError(
                "pulsar_manager_setup_blocker: missing_login_material; "
                f"evidence={self.evidence.path.as_posix()}"
            )

        status = _pulsar_manager_auth_status(
            self.config.pulsar_manager_url,
            self.config.pulsar_manager_password,
            self.config.timeout_seconds,
        )
        self.evidence.record(
            "pulsar_manager_management",
            _pulsar_manager_management_evidence(
                result="passed" if status["passed"] else "failed",
                csrf_available=bool(status["csrf_available"]),
                configured_login_valid=bool(status["configured_login_valid"]),
                redacted_failure_reason=str(status["redacted_failure_reason"]),
            ),
        )
        if not status["passed"]:
            raise AssertionError(
                "pulsar_manager_managed_credential_incomplete: "
                f"{status['redacted_failure_reason']}; evidence={self.evidence.path.as_posix()}"
            )


def _service_checks(
    dashboard_url: str,
    *,
    model_repository: PortEffectiveAccessModelRepository | None = None,
) -> tuple[ServiceCheck, ...]:
    safe_dashboard_url = _validated_local_url(dashboard_url, "dashboard")
    checks: list[ServiceCheck] = [
        ServiceCheck("service-access", safe_dashboard_url),
    ]
    expectations = browser_route_expectations(model_repository)
    routed_hostnames = {
        hostname
        for expectation in expectations
        if (hostname := urlparse(expectation.dashboard_url).hostname) is not None
    }

    for expectation in expectations:
        route_name = expectation.route_name
        browser_statuses = (
            (200,)
            if route_name == "service-access"
            else SERVICE_ALLOWED_STATUSES.get(route_name, (200,))
        )
        allowed_statuses = tuple(
            dict.fromkeys((*browser_statuses, *DASHBOARD_REDIRECT_STATUSES))
        )
        checks.append(
            ServiceCheck(
                f"service-access-route:{route_name}",
                _validated_service_route_url(
                    expectation.dashboard_url,
                    routed_hostnames=routed_hostnames,
                ),
                follow_redirects=False,
                allowed_statuses=allowed_statuses,
            )
        )
    return tuple(checks)


def _routed_hostnames(
    model_repository: PortEffectiveAccessModelRepository | None = None,
) -> set[str]:
    return {
        hostname
        for expectation in browser_route_expectations(model_repository)
        if (hostname := urlparse(expectation.dashboard_url).hostname) is not None
    }


def _validated_service_route_url(
    raw_url: str,
    *,
    routed_hostnames: set[str] | None = None,
) -> str:
    parsed = urlparse(raw_url)
    if parsed.hostname == "localhost":
        return _validated_local_url(raw_url, "dashboard")
    allowed_hostnames = routed_hostnames if routed_hostnames is not None else _routed_hostnames()
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hostnames
        or parsed.port is not None
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise AssertionError("post_install_browser_setup_blocker: invalid_service_route_url")
    return raw_url


def _https_route_checks(
    base_domain: str,
    *,
    model_repository: PortEffectiveAccessModelRepository | None = None,
) -> tuple[ServiceCheck, ...]:
    validated_base_domain = _validated_ingress_base_domain(base_domain)
    return tuple(
        ServiceCheck(
            expectation.route_name,
            _url_for_base_domain(expectation.dashboard_url, validated_base_domain),
            allowed_statuses=SERVICE_ALLOWED_STATUSES.get(
                expectation.route_name,
                (200,),
            ),
        )
        for expectation in browser_route_expectations(model_repository)
    )


def _url_for_base_domain(url: str, base_domain: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname is None:
        raise AssertionError("post_install_browser_setup_blocker: missing_route_hostname")
    hostname_prefix = parsed.hostname.split(".", maxsplit=1)[0]
    return parsed._replace(netloc=f"{hostname_prefix}.{base_domain}").geturl()


def _hostname_for_check(check: ServiceCheck) -> str:
    hostname = urlparse(check.url).hostname
    if hostname is None:
        raise AssertionError("post_install_browser_setup_blocker: missing_route_hostname")
    return hostname


def _hostname_resolves(hostname: str) -> bool:
    try:
        return bool(socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM))
    except OSError:
        return False


def _hostname_resolution_evidence(
    *,
    service: str,
    hostname: str,
    resolved: bool,
) -> dict[str, object]:
    return {
        "hostname": hostname,
        "redacted_failure_reason": "" if resolved else "hostname_unresolved",
        "result": "passed" if resolved else "blocked",
        "service": service,
    }


def _wait_for_service_readiness(
    checks: tuple[ServiceCheck, ...],
    timeout_seconds: float,
    *,
    tls_ca_bundle: str | None = None,
    per_probe_timeout_seconds: float = 5.0,
    retry_interval_seconds: float = 0.25,
    probe: Callable[..., HttpProbeResult] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[tuple[HttpProbeResult, ...], ReadinessSummary]:
    if timeout_seconds <= 0 or per_probe_timeout_seconds <= 0:
        raise ValueError("readiness timeouts must be positive")
    if retry_interval_seconds < 0:
        raise ValueError("readiness retry interval must not be negative")

    started_at = monotonic()
    deadline = started_at + timeout_seconds
    selected_probe = probe or _probe_http
    pending = {check.name: check for check in checks}
    results: dict[str, HttpProbeResult] = {}
    attempts = 0

    if not pending:
        return (), ReadinessSummary(0, 0.0, ())

    while pending:
        if deadline - monotonic() <= 0:
            break
        attempts += 1
        for service, check in tuple(pending.items()):
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            try:
                result = selected_probe(
                    check,
                    min(per_probe_timeout_seconds, remaining),
                    tls_ca_bundle=tls_ca_bundle,
                )
            except Exception as exc:  # The live boundary must preserve a redacted failure.
                result = _failed_probe_result(
                    check,
                    f"probe_exception_{type(exc).__name__}",
                )
            if monotonic() >= deadline:
                results[service] = _failed_probe_result(
                    check,
                    "global_deadline_exceeded",
                )
                break
            results[service] = result
            if result.reachable:
                pending.pop(service)

        if not pending:
            duration = max(0.0, monotonic() - started_at)
            return (
                tuple(results[check.name] for check in checks),
                ReadinessSummary(attempts, duration, ()),
            )

        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        sleep(min(retry_interval_seconds, remaining))

    duration = min(timeout_seconds, max(0.0, monotonic() - started_at))
    pending_services = tuple(check.name for check in checks if check.name in pending)
    summary = ReadinessSummary(attempts, duration, pending_services)
    failure_results = tuple(
        results.get(
            check.name,
            _failed_probe_result(check, "global_deadline_exhausted_before_probe"),
        )
        for check in checks
    )
    raise ReadinessDeadlineExceeded(summary, failure_results)


def _probe_http(
    check: ServiceCheck,
    timeout_seconds: float,
    *,
    tls_ca_bundle: str | None = None,
) -> HttpProbeResult:
    try:
        status_code, content_type = _http_head_or_get(
            check.url,
            timeout_seconds,
            follow_redirects=check.follow_redirects,
            tls_ca_bundle=tls_ca_bundle,
        )
    except OSError as exc:
        return HttpProbeResult(
            service=check.name,
            url=check.url,
            reachable=False,
            status_code=None,
            content_type="",
            result="failed",
            redacted_failure_reason=type(exc).__name__,
        )

    reachable = status_code in check.allowed_statuses
    return HttpProbeResult(
        service=check.name,
        url=check.url,
        reachable=reachable,
        status_code=status_code,
        content_type=content_type,
        result="passed" if reachable else "failed",
        redacted_failure_reason="" if reachable else "http_status_out_of_range",
    )


def _ready_probe_result(check: ServiceCheck) -> HttpProbeResult:
    return HttpProbeResult(
        service=check.name,
        url=check.url,
        reachable=True,
        status_code=200,
        content_type="text/html",
        result="passed",
    )


def _failed_probe_result(
    check: ServiceCheck,
    redacted_failure_reason: str,
) -> HttpProbeResult:
    return HttpProbeResult(
        service=check.name,
        url=check.url,
        reachable=False,
        status_code=None,
        content_type="",
        result="failed",
        redacted_failure_reason=redacted_failure_reason,
    )


def _probe_https_route(
    check: ServiceCheck,
    timeout_seconds: float,
    *,
    tls_ca_bundle: str | None = None,
) -> HttpsRouteProbeResult:
    hostname = _hostname_for_check(check)
    if not _hostname_resolves(hostname):
        return HttpsRouteProbeResult(
            service=check.name,
            hostname=hostname,
            reachable=False,
            status_code=None,
            tls_status="blocked_hostname_resolution",
            result="blocked",
            redacted_failure_reason="hostname_unresolved",
        )
    try:
        status_code, _content_type = _http_head_or_get(
            check.url,
            timeout_seconds,
            follow_redirects=check.follow_redirects,
            tls_ca_bundle=tls_ca_bundle,
        )
    except OSError as exc:
        return HttpsRouteProbeResult(
            service=check.name,
            hostname=hostname,
            reachable=False,
            status_code=None,
            tls_status="tls_or_http_unreachable",
            result="failed",
            redacted_failure_reason=type(exc).__name__,
        )

    reachable = status_code in check.allowed_statuses
    return HttpsRouteProbeResult(
        service=check.name,
        hostname=hostname,
        reachable=reachable,
        status_code=status_code,
        tls_status="https_reachable_verified",
        result="passed" if reachable else "failed",
        redacted_failure_reason="" if reachable else "http_status_out_of_range",
    )


def _http_head_or_get(
    url: str,
    timeout_seconds: float,
    *,
    follow_redirects: bool,
    tls_ca_bundle: str | None = None,
) -> tuple[int, str]:
    request = Request(url, method="HEAD")
    context = _ssl_context_for_url(url, tls_ca_bundle)
    handlers: list[Any] = []
    if not follow_redirects:
        handlers.append(_NoRedirectHandler)
    if context is not None:
        handlers.append(HTTPSHandler(context=context))
    opener = build_opener(*handlers) if handlers else build_opener()
    try:
        response_context = opener.open(request, timeout=timeout_seconds)
    except HTTPError as exc:
        if exc.code < 400:
            status_code = exc.code
            content_type = exc.headers.get("content-type", "")
            exc.close()
            return status_code, content_type
        if exc.code >= 500:
            exc.close()
            raise
        exc.close()
    except OSError:
        pass
    else:
        with response_context as response:
            return int(response.status), response.headers.get("content-type", "")

    request = Request(url, method="GET")
    try:
        response_context = opener.open(request, timeout=timeout_seconds)
    except HTTPError as exc:
        if exc.code < 500:
            status_code = exc.code
            content_type = exc.headers.get("content-type", "")
            exc.close()
            return status_code, content_type
        exc.close()
        raise

    with response_context as response:
        return int(response.status), response.headers.get("content-type", "")


def _missing_infisical_login_material(
    config: LivePostInstallConfig,
) -> tuple[str, ...]:
    missing: list[str] = []
    if not config.infisical_email:
        missing.append("TSW_INFISICAL_LOGIN_EMAIL")
    if not config.infisical_password:
        missing.append("TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD")
    return tuple(missing)


def _missing_infisical_items(config: LivePostInstallConfig) -> tuple[str, ...]:
    if config.infisical_email is None or config.infisical_password is None:
        raise AssertionError("infisical_setup_blocker: missing_login_material")

    session = requests.Session()
    organization_token = _infisical_organization_token(session, config)
    project_id = _infisical_project_id(session, config, organization_token)
    present_keys = _infisical_secret_keys(session, config, organization_token, project_id)
    return tuple(
        item
        for item in EXPECTED_INFISICAL_ITEMS
        if EXPECTED_INFISICAL_ITEM_KEYS[item] not in present_keys
    )


@dataclass(frozen=True)
class _InfisicalManagementStatus:
    installed: bool
    super_admin_present: bool
    project_present: bool
    present_password_count: int
    missing_password_count: int
    redacted_failure_reason: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.installed
            and self.super_admin_present
            and self.project_present
            and self.missing_password_count == 0
        )


def _infisical_management_status(
    config: LivePostInstallConfig,
    expected_password_keys: tuple[str, ...],
) -> _InfisicalManagementStatus:
    try:
        session = requests.Session()
        health = session.get(
            urljoin(config.infisical_url.rstrip("/") + "/", "api/status"),
            timeout=config.timeout_seconds,
            verify=_requests_tls_verify(config),
        )
    except requests.RequestException as exc:
        return _InfisicalManagementStatus(
            False,
            False,
            False,
            0,
            len(expected_password_keys),
            type(exc).__name__,
        )
    if health.status_code != 200:
        return _InfisicalManagementStatus(
            False,
            False,
            False,
            0,
            len(expected_password_keys),
            "infisical_status_unavailable",
        )

    try:
        organization_token = _infisical_organization_token(session, config)
        project_id = _infisical_project_id(session, config, organization_token)
        present_keys = _infisical_secret_keys(session, config, organization_token, project_id)
    except requests.RequestException as exc:
        return _InfisicalManagementStatus(
            True,
            False,
            False,
            0,
            len(expected_password_keys),
            type(exc).__name__,
        )
    except AssertionError as exc:
        reason = str(exc) or "infisical_api_contract_failed"
        super_admin_present = reason not in {"admin_login_failed", "organization_missing"}
        project_present = reason != "project_missing" and super_admin_present
        return _InfisicalManagementStatus(
            True,
            super_admin_present,
            project_present,
            0,
            len(expected_password_keys),
            reason,
        )

    missing = tuple(key for key in expected_password_keys if key not in present_keys)
    return _InfisicalManagementStatus(
        installed=True,
        super_admin_present=True,
        project_present=True,
        present_password_count=len(expected_password_keys) - len(missing),
        missing_password_count=len(missing),
        redacted_failure_reason="" if not missing else "credential_entries_missing",
    )


def _infisical_organization_token(
    session: requests.Session,
    config: LivePostInstallConfig,
) -> str:
    response = session.post(
        urljoin(config.infisical_url.rstrip("/") + "/", "api/v3/auth/login"),
        json={
            "email": config.infisical_email,
            "password": config.infisical_password,
        },
        timeout=config.timeout_seconds,
        verify=_requests_tls_verify(config),
    )
    if response.status_code != 200:
        raise AssertionError("admin_login_failed")
    login_token = response.json().get("accessToken")
    if not isinstance(login_token, str) or not login_token:
        raise AssertionError("admin_login_failed")
    headers = {"Authorization": f"Bearer {login_token}"}
    organizations = session.get(
        urljoin(config.infisical_url.rstrip("/") + "/", "api/v1/organization"),
        headers=headers,
        timeout=config.timeout_seconds,
        verify=_requests_tls_verify(config),
    )
    if organizations.status_code != 200:
        raise AssertionError("organization_missing")
    organization_items = organizations.json().get("organizations")
    if not isinstance(organization_items, list) or not organization_items:
        raise AssertionError("organization_missing")
    organization_id = organization_items[0].get("id")
    if not isinstance(organization_id, str) or not organization_id:
        raise AssertionError("organization_missing")
    selected = session.post(
        urljoin(config.infisical_url.rstrip("/") + "/", "api/v3/auth/select-organization"),
        headers=headers,
        json={"organizationId": organization_id},
        timeout=config.timeout_seconds,
        verify=_requests_tls_verify(config),
    )
    if selected.status_code != 200:
        raise AssertionError("organization_missing")
    token = selected.json().get("token")
    if not isinstance(token, str) or not token:
        raise AssertionError("organization_missing")
    return token


def _infisical_project_id(
    session: requests.Session,
    config: LivePostInstallConfig,
    organization_token: str,
) -> str:
    response = session.get(
        urljoin(config.infisical_url.rstrip("/") + "/", "api/v1/projects"),
        headers={"Authorization": f"Bearer {organization_token}"},
        timeout=config.timeout_seconds,
        verify=_requests_tls_verify(config),
    )
    if response.status_code != 200:
        raise AssertionError("project_missing")
    projects = response.json().get("projects")
    if not isinstance(projects, list):
        raise AssertionError("project_missing")
    for project in projects:
        if not isinstance(project, dict):
            continue
        names = {
            str(project.get("name", "")),
            str(project.get("projectName", "")),
            str(project.get("slug", "")),
        }
        if "tiny-swarm-world" in names:
            project_id = project.get("id")
            if isinstance(project_id, str) and project_id:
                return project_id
    raise AssertionError("project_missing")


def _infisical_secret_keys(
    session: requests.Session,
    config: LivePostInstallConfig,
    organization_token: str,
    project_id: str,
) -> set[str]:
    response = session.get(
        urljoin(
            config.infisical_url.rstrip("/") + "/",
            f"api/v3/secrets/raw?workspaceId={project_id}&environment=local&secretPath=%2F",
        ),
        headers={"Authorization": f"Bearer {organization_token}"},
        timeout=config.timeout_seconds,
        verify=_requests_tls_verify(config),
    )
    if response.status_code != 200:
        raise AssertionError("credential_entries_missing")
    payload = response.json()
    secrets = payload.get("secrets")
    if not isinstance(secrets, list):
        raise AssertionError("credential_entries_missing")
    keys: set[str] = set()
    for item in secrets:
        if not isinstance(item, dict):
            continue
        key = item.get("secretKey") or item.get("key")
        if isinstance(key, str):
            keys.add(key)
    return keys


def _sonarqube_auth_valid(
    base_url: str,
    username: str,
    password: str,
    timeout_seconds: float,
) -> bool:
    response = requests.get(
        urljoin(base_url.rstrip("/") + "/", "api/authentication/validate"),
        auth=(username, password),
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        return False
    payload = response.json()
    return isinstance(payload, dict) and payload.get("valid") is True


def _pulsar_admin_auth_status(
    base_url: str,
    token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    clusters_url = urljoin(base_url.rstrip("/") + "/", "admin/v2/clusters")
    try:
        unauthenticated = requests.get(clusters_url, timeout=timeout_seconds)
    except requests.RequestException as exc:
        fallback = _pulsar_admin_auth_status_from_lxc(token)
        if fallback["passed"]:
            return fallback
        fallback["redacted_failure_reason"] = type(exc).__name__
        return fallback
    unauthenticated_rejected = unauthenticated.status_code in {401, 403}
    try:
        authenticated = requests.get(
            clusters_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        return {
            "configured_login_valid": False,
            "passed": False,
            "redacted_failure_reason": type(exc).__name__,
            "unauthenticated_rejected": unauthenticated_rejected,
        }
    configured_login_valid = (
        authenticated.status_code == 200 and "standalone" in authenticated.text.casefold()
    )
    return {
        "configured_login_valid": configured_login_valid,
        "passed": unauthenticated_rejected and configured_login_valid,
        "redacted_failure_reason": (
            ""
            if unauthenticated_rejected and configured_login_valid
            else "managed_login_inactive"
        ),
        "unauthenticated_rejected": unauthenticated_rejected,
    }


def _pulsar_admin_auth_status_from_lxc(token: str) -> dict[str, object]:
    container = _pulsar_container_id_from_lxc()
    if not container:
        return {
            "configured_login_valid": False,
            "passed": False,
            "redacted_failure_reason": "pulsar_container_missing",
            "unauthenticated_rejected": False,
        }
    probe = """
read AUTH_TOKEN
export AUTH_TOKEN
python3 - <<'PY'
import os
from urllib import error, request

url = "http://localhost:8080/admin/v2/clusters"

def status(headers=None):
    req = request.Request(url, headers=headers or {})
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")

unauthenticated_status, _ = status()
authenticated_status, authenticated_body = status(
    {"Authorization": "Bearer " + os.environ.get("AUTH_TOKEN", "")}
)
print(unauthenticated_status)
print(authenticated_status)
print("standalone" in authenticated_body.casefold())
PY
"""
    result = subprocess.run(
        [
            "lxc",
            "exec",
            "swarm-manager",
            "--",
            "docker",
            "exec",
            "-i",
            container,
            "sh",
            "-c",
            probe,
        ],
        input=f"{token}\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) < 3:
        return {
            "configured_login_valid": False,
            "passed": False,
            "redacted_failure_reason": "lxc_pulsar_probe_failed",
            "unauthenticated_rejected": False,
        }
    unauthenticated_rejected = lines[0] in {"401", "403"}
    configured_login_valid = lines[1] == "200" and lines[2] == "True"
    return {
        "configured_login_valid": configured_login_valid,
        "passed": unauthenticated_rejected and configured_login_valid,
        "redacted_failure_reason": (
            ""
            if unauthenticated_rejected and configured_login_valid
            else "managed_login_inactive"
        ),
        "unauthenticated_rejected": unauthenticated_rejected,
    }


def _pulsar_manager_auth_status(
    base_url: str,
    password: str,
    timeout_seconds: float,
) -> dict[str, object]:
    session = requests.Session()
    manager_url = base_url.rstrip() + "/"
    csrf_url = urljoin(manager_url, "pulsar-manager/csrf-token")
    login_url = urljoin(manager_url, "pulsar-manager/login")
    try:
        csrf_response = session.get(
            csrf_url,
            headers={"Host": "localhost:14081"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        return {
            "configured_login_valid": False,
            "csrf_available": False,
            "passed": False,
            "redacted_failure_reason": type(exc).__name__,
        }
    csrf_available = csrf_response.status_code == 200 and bool(csrf_response.text.strip())
    headers = {
        "Content-Type": "application/json",
        "Host": "localhost:14081",
    }
    if csrf_available:
        csrf_token = csrf_response.text.strip()
        headers["X-XSRF-TOKEN"] = csrf_token
        session.cookies.set("XSRF-TOKEN", csrf_token)
    try:
        login_response = session.post(
            login_url,
            json={
                "username": "admin",
                "password": password,
            },
            headers=headers,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        return {
            "configured_login_valid": False,
            "csrf_available": csrf_available,
            "passed": False,
            "redacted_failure_reason": type(exc).__name__,
        }
    configured_login_valid = False
    if login_response.status_code == 200:
        try:
            configured_login_valid = login_response.json().get("login") == "success"
        except requests.JSONDecodeError:
            configured_login_valid = False
    return {
        "configured_login_valid": configured_login_valid,
        "csrf_available": csrf_available,
        "passed": csrf_available and configured_login_valid,
        "redacted_failure_reason": (
            "" if csrf_available and configured_login_valid else "managed_login_inactive"
        ),
    }


def _pulsar_container_id_from_lxc() -> str:
    result = subprocess.run(
        [
            "lxc",
            "exec",
            "swarm-manager",
            "--",
            "docker",
            "ps",
            "--filter",
            "name=pulsar_pulsar",
            "--format",
            "{{.ID}}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")


def _fill_first(page: Any, labels: tuple[str, ...], value: str) -> None:
    last_error: Exception | None = None
    for label in labels:
        for locator in (
            page.get_by_label(label, exact=False),
            page.get_by_placeholder(label, exact=False),
        ):
            try:
                locator.fill(value, timeout=5_000)
                return
            except Exception as exc:
                last_error = exc
    raise RuntimeError(f"could not fill field: {labels}; last={type(last_error).__name__}")


def _click_first(page: Any, names: tuple[str, ...]) -> None:
    last_error: Exception | None = None
    for name in names:
        for locator in (
            page.get_by_role("button", name=name, exact=False),
            page.get_by_text(name, exact=False),
            page.locator(f"input[type='submit'][value*='{name}']"),
        ):
            try:
                locator.first.click(timeout=10_000)
                return
            except Exception as exc:
                last_error = exc
    raise RuntimeError(f"could not click control: {names}; last={type(last_error).__name__}")


def _click_first_optional(page: Any, names: tuple[str, ...]) -> None:
    try:
        _click_first(page, names)
    except RuntimeError:
        return


def _infisical_item_evidence(
    *,
    expected_item: str,
    item_present: bool,
    result: str,
    redacted_failure_reason: str,
) -> dict[str, object]:
    return {
        "expected_infisical_item": expected_item,
        "item_present": item_present,
        "redacted_failure_reason": redacted_failure_reason,
        "result": result,
        "service": expected_item.removeprefix("platform/"),
    }


def _infisical_management_evidence(
    *,
    result: str,
    installed: bool,
    super_admin_present: bool,
    project_present: bool,
    expected_credential_count: int,
    present_credential_count: int,
    redacted_failure_reason: str,
) -> dict[str, object]:
    return {
        "expected_credential_count": expected_credential_count,
        "installed": installed,
        "present_credential_count": present_credential_count,
        "project_present": project_present,
        "redacted_failure_reason": redacted_failure_reason,
        "result": result,
        "service": "infisical",
        "super_admin_present": super_admin_present,
    }


def _sonarqube_management_evidence(
    *,
    result: str,
    configured_login_valid: bool,
    default_login_disabled: bool,
    redacted_failure_reason: str,
) -> dict[str, object]:
    return {
        "configured_login_valid": configured_login_valid,
        "default_login_disabled": default_login_disabled,
        "redacted_failure_reason": redacted_failure_reason,
        "result": result,
        "service": "sonarqube",
    }


def _pulsar_management_evidence(
    *,
    result: str,
    unauthenticated_rejected: bool,
    configured_login_valid: bool,
    redacted_failure_reason: str,
) -> dict[str, object]:
    return {
        "configured_login_valid": configured_login_valid,
        "redacted_failure_reason": redacted_failure_reason,
        "result": result,
        "service": "pulsar",
        "unauthenticated_rejected": unauthenticated_rejected,
    }


def _pulsar_manager_management_evidence(
    *,
    result: str,
    csrf_available: bool,
    configured_login_valid: bool,
    redacted_failure_reason: str,
) -> dict[str, object]:
    return {
        "configured_login_valid": configured_login_valid,
        "csrf_available": csrf_available,
        "redacted_failure_reason": redacted_failure_reason,
        "result": result,
        "service": "pulsar-manager",
    }


def _expected_infisical_password_keys() -> tuple[str, ...]:
    keys: list[str] = []
    manifest = YAML(typ="safe").load(INFISICAL_SECRET_MANIFEST.read_text(encoding="utf-8")) or {}
    for entry in manifest.get("secrets", []):
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        if (
            isinstance(key, str)
            and entry.get("required") is True
            and any(key.endswith(suffix) for suffix in MANAGED_CREDENTIAL_KEY_SUFFIXES)
        ):
            keys.append(key)
    return tuple(dict.fromkeys(keys))


def _env_value(local_env: dict[str, str], key: str, default: str) -> str:
    return os.environ.get(key) or local_env.get(key) or default


def _env_optional(local_env: dict[str, str], key: str) -> str | None:
    return os.environ.get(key) or local_env.get(key)


def _validated_local_url(raw_url: str, purpose: str) -> str:
    try:
        parsed = urlparse(raw_url)
        port = parsed.port
    except ValueError as exc:
        raise AssertionError(_invalid_local_url_reason(purpose)) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname != "localhost"
        or parsed.username
        or parsed.password
        or parsed.query
        or (parsed.fragment and purpose != "dashboard")
        or port is not None
        and not 1 <= port <= 65535
    ):
        raise AssertionError(_invalid_local_url_reason(purpose))
    return raw_url


def _validated_ingress_base_domain(raw_domain: str) -> str:
    domain = raw_domain.strip().casefold().rstrip(".")
    if not domain or domain == "localhost" or domain.replace(".", "").isdigit():
        raise AssertionError("post_install_browser_setup_blocker: invalid_ingress_base_domain")
    try:
        desired_https_ingress_for_profile(
            ServiceStackProfile.SERVICE_ACCESS,
            base_domain=domain,
            port_registry=PortRegistryYamlRepository().load(),
        )
    except ValueError as exc:
        raise AssertionError(
            "post_install_browser_setup_blocker: invalid_ingress_base_domain"
        ) from exc
    return domain


def _validated_tls_ca_bundle(raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_file():
        raise AssertionError("post_install_browser_setup_blocker: invalid_tls_ca_bundle")
    return raw_path


def _canonical_tls_contract_resolver(
    environment: dict[str, str],
) -> PortTlsContractResolver:
    return LocalTlsContractResolver(
        state_root=canonical_tls_state_root(environment),
        certificate_secret_name=environment.get(
            TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
            DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
        )
        or DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
        private_key_secret_name=environment.get(
            TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
            DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
        )
        or DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
        environment=environment,
    )


def _canonical_live_trust_bundle(
    tls_contract_resolver: PortTlsContractResolver,
) -> str:
    try:
        trust_bundle = tls_contract_resolver.resolve().trust_bundle
    except TlsContractConfigurationError as exc:
        raise AssertionError(
            "post_install_browser_setup_blocker: invalid_tls_ca_bundle"
        ) from exc
    validated = _validated_tls_ca_bundle(str(trust_bundle))
    if validated is None:
        raise AssertionError("post_install_browser_setup_blocker: invalid_tls_ca_bundle")
    return validated


def _ssl_context_for_url(url: str, tls_ca_bundle: str | None = None) -> ssl.SSLContext | None:
    if not url.startswith("https://"):
        return None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if tls_ca_bundle is None:
        context.load_default_certs()
    else:
        context.load_verify_locations(cafile=tls_ca_bundle)
    return context


def _requests_tls_verify(config: LivePostInstallConfig) -> bool | str:
    return config.tls_ca_bundle or True


def _invalid_local_url_reason(purpose: str) -> str:
    if purpose == "infisical":
        return "infisical_setup_blocker: invalid_local_infisical_url"
    return f"post_install_browser_setup_blocker: invalid_local_{purpose}_url"


def _load_shell_environment(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


@dataclass(frozen=True)
class _DashboardReferences:
    credential_items: tuple[str, ...]
    no_login_services: tuple[str, ...]


class _DashboardReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.credential_items: list[str] = []
        self.no_login_services: list[str] = []
        self._current_row_header = ""
        self._in_header = False
        self._in_code = False

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag == "th":
            self._in_header = True
            self._current_row_header = ""
        if tag == "code":
            self._in_code = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "th":
            self._in_header = False
        if tag == "code":
            self._in_code = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_header:
            self._current_row_header = text
        if self._in_code and text.startswith("platform/"):
            self.credential_items.append(text)
        if self._in_code and text == "not required" and self._current_row_header:
            self.no_login_services.append(self._current_row_header)


def _dashboard_references(path: Path) -> _DashboardReferences:
    parser = _DashboardReferenceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return _DashboardReferences(
        credential_items=tuple(dict.fromkeys(parser.credential_items)),
        no_login_services=tuple(dict.fromkeys(parser.no_login_services)),
    )


class _EvidenceRecorder:
    def __init__(self, root: Path) -> None:
        ensure_secure_directory(root)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = root / timestamp
        self.path.mkdir(mode=0o700, exist_ok=False)
        ensure_secure_directory(self.path)
        self._records: list[dict[str, object]] = []

    def record(self, kind: str, payload: dict[str, object]) -> None:
        record = {"kind": kind, **payload}
        if not _evidence_safe(record):
            raise AssertionError("redacted_evidence_policy_failed")
        self._records.append(record)

    def write(self) -> None:
        payload = {
            "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "records": self._records,
        }
        if not _evidence_safe(payload):
            raise AssertionError("redacted_evidence_policy_failed")
        (self.path / "summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _evidence_safe(value: object) -> bool:
    if isinstance(value, dict):
        return all(
            _evidence_safe(str(key)) and _evidence_safe(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_evidence_safe(item) for item in value)
    text = str(value).casefold()
    return not any(fragment.casefold() in text for fragment in FORBIDDEN_EVIDENCE_FRAGMENTS)


class _FakeMonotonicClock:
    def __init__(self) -> None:
        self.current = 0.0

    def __call__(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


if __name__ == "__main__":
    unittest.main()
