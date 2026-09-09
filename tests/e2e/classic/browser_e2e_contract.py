from __future__ import annotations

import json
import os
import re
import time
import unittest
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from unittest.mock import Mock, patch
from urllib.parse import urlparse

from tiny_swarm_world.application.ports.repositories.port_effective_access_model_repository import (
    PortEffectiveAccessModelRepository,
)
from tiny_swarm_world.infrastructure.adapters.repositories.compose_file_repository_yaml import (
    ComposeFileRepositoryYaml,
)
from tests.support.effective_access_model_fixture import effective_access_model_fixture
from tools.live.secure_runtime_paths import ensure_secure_directory

webdriver: Any
By: Any
try:
    from selenium import webdriver as imported_webdriver  # type: ignore[import-not-found]
    from selenium.webdriver.common.by import By as imported_by  # type: ignore[import-not-found]
except ModuleNotFoundError:
    webdriver = None
    By = None
else:
    webdriver = imported_webdriver
    By = imported_by


RUN_LIVE_ENV = "TSW_RUN_POST_INSTALL_BROWSER_LIVE"
E2E_EVIDENCE_ROOT = Path(".tiny-swarm-world/evidence/classic-public-beta-rc1")
LOGIN_REQUIRED_ROUTES = frozenset(
    {
        "infisical",
        "jenkins",
        "nexus",
        "portainer",
        "pulsar-manager",
        "sonarqube",
    }
)
SUITE_STATUSES = ("passed", "failed", "skipped", "missing")


@dataclass(frozen=True)
class BrowserRouteExpectation:
    route_name: str
    dashboard_url: str


@dataclass(frozen=True)
class BrowserRouteResult:
    route_name: str
    url: str
    result: str
    redacted_reason: str = ""

    def to_evidence(self) -> dict[str, object]:
        return {
            "evidence_kind": "routed_browser_e2e_result",
            "redacted_reason": self.redacted_reason,
            "result": self.result,
            "route_name": self.route_name,
            "status": self.result,
            "url": self.url,
        }


def browser_route_expectations(
    model_repository: PortEffectiveAccessModelRepository | None = None,
) -> tuple[BrowserRouteExpectation, ...]:
    repository = model_repository or ComposeFileRepositoryYaml()
    model_payload = repository.get_effective_access_model().to_dict()
    raw_links = model_payload.get("service_access_links")
    if not isinstance(raw_links, list):
        raise AssertionError("effective access model must provide service_access_links")

    expectations: dict[str, BrowserRouteExpectation] = {}
    for raw_link in raw_links:
        if not isinstance(raw_link, dict):
            raise AssertionError("service_access_links entries must be mappings")
        route_name = raw_link.get("service")
        dashboard_url = raw_link.get("url")
        if not isinstance(route_name, str) or not route_name:
            raise AssertionError("service access link must identify its route")
        if not isinstance(dashboard_url, str) or not dashboard_url:
            raise AssertionError("service access link must provide its routed URL")
        if route_name in expectations:
            raise AssertionError(f"duplicate browser route expectation: {route_name}")
        expectations[route_name] = BrowserRouteExpectation(
            route_name=route_name,
            dashboard_url=dashboard_url,
        )
    return tuple(expectations[name] for name in sorted(expectations))


def route_expectation_for_browser(
    route_name: str,
    model_repository: PortEffectiveAccessModelRepository | None = None,
) -> BrowserRouteExpectation:
    for expectation in browser_route_expectations(model_repository):
        if expectation.route_name == route_name:
            return expectation
    raise unittest.SkipTest(
        f"route is not active in the effective access model: {route_name}"
    )


def live_e2e_enabled() -> bool:
    return os.environ.get(RUN_LIVE_ENV) == "1"


def live_browser_evidence_root() -> Path:
    """Resolve and qualify the shared protected browser evidence root."""
    configured = (
        os.environ.get("TSW_LIVE_EVIDENCE_ROOT", "").strip()
        or os.environ.get("TSW_CLASSIC_EVIDENCE_ROOT", "").strip()
    )
    state = os.environ.get("XDG_STATE_HOME", "").strip()
    root = (
        Path(configured).expanduser()
        if configured
        else (Path(state).expanduser() if state else Path.home() / ".local/state")
        / "tiny-swarm-world/evidence/classic-public-beta-rc1"
    )
    root = root.absolute()
    ensure_secure_directory(root)
    return root


def approved_credential_available(route_name: str) -> bool:
    return _approved_credential(route_name) is not None


def selenium_driver():
    if webdriver is None or By is None:
        raise unittest.SkipTest("selenium is not installed in the active test environment")
    return webdriver, By


class BrowserRouteE2EContract:
    route_name: str = ""
    expected_title_fragment: str = ""

    def test_route_contract_uses_routed_https_url(self) -> None:
        _assert_routed_https_url(self, route_expectation_for_browser(self.route_name).dashboard_url)

    def test_live_e2e_evidence_target_is_local_and_ignored(self) -> None:
        _assert_evidence_target(self)

    def test_live_routed_link_opens_with_selenium(self) -> None:
        testcase = cast(unittest.TestCase, self)
        expectation = route_expectation_for_browser(self.route_name)
        if not live_e2e_enabled():
            _record_route_result(
                BrowserRouteResult(
                    self.route_name,
                    expectation.dashboard_url,
                    "skipped",
                    "blocked_live_consent_missing",
                )
            )
            testcase.skipTest(f"set {RUN_LIVE_ENV}=1 to run routed Selenium browser E2E checks")
        live_browser_evidence_root()
        try:
            selenium_webdriver, by = selenium_driver()
        except unittest.SkipTest:
            _record_route_result(
                BrowserRouteResult(
                    self.route_name,
                    expectation.dashboard_url,
                    "skipped",
                    "blocked_selenium_unavailable",
                )
            )
            raise
        options = selenium_webdriver.FirefoxOptions()
        options.add_argument("-headless")

        driver = selenium_webdriver.Firefox(options=options)
        try:
            driver.set_page_load_timeout(
                float(os.environ.get("TSW_BROWSER_E2E_TIMEOUT_SECONDS", "45"))
            )
            driver.get(expectation.dashboard_url)
            testcase.assertTrue(
                _browser_navigation_reached_expected_host(
                    driver.current_url,
                    expectation.dashboard_url,
                ),
                "expected browser navigation to reach the routed HTTPS host",
            )
            if self.route_name in LOGIN_REQUIRED_ROUTES:
                credential = _approved_credential(self.route_name)
                if credential is None:
                    _record_route_result(
                        BrowserRouteResult(
                            self.route_name,
                            expectation.dashboard_url,
                            "skipped",
                            "blocked_missing_credential_source",
                        )
                    )
                    testcase.skipTest(
                        "approved credential source unavailable for required login flow"
                    )
                _perform_login_flow(driver, by, self.route_name, credential)
                body_text, title = _wait_for_post_login_success(
                    driver,
                    by,
                    self.route_name,
                )
                testcase.assertTrue(
                    _post_login_success(self.route_name, body_text, title),
                    "expected stable authenticated landing state after login",
                )
            _record_route_result(
                BrowserRouteResult(
                    self.route_name,
                    expectation.dashboard_url,
                    "passed",
                )
            )
        except unittest.SkipTest:
            raise
        except Exception as exc:
            _record_route_result(
                BrowserRouteResult(
                    self.route_name,
                    expectation.dashboard_url,
                    "failed",
                    _redacted_failure_reason(exc),
                )
            )
            raise
        finally:
            driver.quit()


class BrowserRouteE2EContractStaticTest(unittest.TestCase):
    def test_first_present_waits_for_delayed_spa_selector(self) -> None:
        expected_element = Mock()
        driver = Mock()
        driver.find_element.side_effect = [LookupError("not rendered"), expected_element]
        sleep_calls: list[float] = []

        actual = _first_present(
            driver,
            Mock(CSS_SELECTOR="css selector"),
            ("input[name='username']",),
            attempts=2,
            retry_interval_seconds=0.25,
            sleep=sleep_calls.append,
        )

        self.assertIs(expected_element, actual)
        self.assertEqual(sleep_calls, [0.25])

    def test_page_text_retries_after_stale_spa_body(self) -> None:
        body = Mock(text="Projects")
        driver = Mock(title="SonarQube")
        driver.find_element.side_effect = [LookupError("stale body"), body]
        sleep_calls: list[float] = []

        actual = _page_text_and_title(
            driver,
            Mock(TAG_NAME="tag name"),
            attempts=2,
            retry_interval_seconds=0.25,
            sleep=sleep_calls.append,
        )

        self.assertEqual(actual, ("Projects", "SonarQube"))
        self.assertEqual(sleep_calls, [0.25])

    def test_post_login_wait_rechecks_spa_landing_state(self) -> None:
        sleep_calls: list[float] = []
        with patch(
            "tests.e2e.classic.browser_e2e_contract._page_text_and_title",
            side_effect=[("Sign in", "SonarQube"), ("Projects", "SonarQube")],
        ):
            actual = _wait_for_post_login_success(
                Mock(),
                Mock(),
                "sonarqube",
                attempts=2,
                retry_interval_seconds=0.25,
                sleep=sleep_calls.append,
            )

        self.assertEqual(actual, ("Projects", "SonarQube"))
        self.assertEqual(sleep_calls, [0.25])

    def test_product_brand_alone_is_not_an_authenticated_landing_state(self) -> None:
        for route_name in sorted(LOGIN_REQUIRED_ROUTES):
            with self.subTest(route_name=route_name):
                self.assertFalse(
                    _post_login_success(
                        route_name,
                        f"Sign in to {route_name}",
                        route_name,
                    )
                )

    def test_pulsar_manager_environment_listing_is_an_authenticated_landing_state(self) -> None:
        self.assertTrue(
            _post_login_success(
                "pulsar-manager",
                "New Environment",
                "Pulsar Admin UI",
            )
        )

    def test_all_browser_route_urls_use_routed_https_hosts(self) -> None:
        for expectation in browser_route_expectations():
            with self.subTest(route=expectation.route_name):
                _assert_routed_https_url(self, expectation.dashboard_url)

    def test_enabled_optional_routes_are_derived_from_effective_model_links(self) -> None:
        with effective_access_model_fixture(
            enabled_services=("prometheus", "grafana", "tiny-swarm")
        ) as fixture:
            expectations = browser_route_expectations(fixture.repository)

        urls_by_route = {
            expectation.route_name: expectation.dashboard_url
            for expectation in expectations
        }
        self.assertEqual(urls_by_route["prometheus"], "https://prometheus.tsw.local")
        self.assertEqual(urls_by_route["grafana"], "https://grafana.tsw.local")
        self.assertEqual(urls_by_route["app"], "https://app.tsw.local")
        self.assertEqual(urls_by_route["api"], "https://api.tsw.local")

    def test_disabled_routes_and_stale_files_do_not_define_suite_membership(self) -> None:
        with effective_access_model_fixture() as fixture:
            expectations = browser_route_expectations(fixture.repository)
            with self.assertRaises(unittest.SkipTest):
                route_expectation_for_browser("prometheus", fixture.repository)

        summary = build_suite_summary(
            expectations,
            {
                "prometheus": {
                    "route_name": "prometheus",
                    "status": "failed",
                    "url": "https://prometheus.tsw.local",
                }
            },
        )
        status_matrix = cast(dict[str, list[str]], summary["status_matrix"])
        represented_routes = {
            route_name
            for route_names in status_matrix.values()
            for route_name in route_names
        }
        self.assertFalse(
            represented_routes & {"prometheus", "grafana", "app", "api"}
        )

    def test_suite_summary_partitions_each_expected_route_once(self) -> None:
        expectations = tuple(
            BrowserRouteExpectation(name, f"https://{name}.tsw.local")
            for name in ("passed-route", "failed-route", "skipped-route", "missing-route")
        )
        summary = build_suite_summary(
            expectations,
            {
                "passed-route": {"status": "passed"},
                "failed-route": {"status": "failed"},
                "skipped-route": {"status": "skipped"},
            },
        )

        self.assertEqual(
            summary["status_matrix"],
            {
                "passed": ["passed-route"],
                "failed": ["failed-route"],
                "skipped": ["skipped-route"],
                "missing": ["missing-route"],
            },
        )
        route_results = cast(list[dict[str, object]], summary["route_results"])
        self.assertEqual(len(route_results), 4)
        self.assertEqual(len({result["route_name"] for result in route_results}), 4)
        self.assertEqual(summary["result"], "failed")

    def test_missing_route_is_explicit_and_never_successful(self) -> None:
        summary = build_suite_summary(
            (
                BrowserRouteExpectation(
                    "service-access",
                    "https://service-access.tsw.local",
                ),
            ),
            {},
        )

        route_result = cast(list[dict[str, object]], summary["route_results"])[0]
        self.assertEqual(route_result["status"], "missing")
        self.assertEqual(route_result["result"], "missing")
        self.assertEqual(route_result["redacted_reason"], "missing_route_evidence")
        self.assertEqual(summary["result"], "failed")

    def test_suite_summary_is_deterministic_and_only_skipped_is_skipped(self) -> None:
        expectations = (
            BrowserRouteExpectation("swagger", "https://swagger.tsw.local"),
            BrowserRouteExpectation("service-access", "https://service-access.tsw.local"),
        )
        evidence = {
            "service-access": {"status": "skipped"},
            "swagger": {"status": "skipped"},
        }

        first = build_suite_summary(expectations, evidence)
        second = build_suite_summary(tuple(reversed(expectations)), dict(reversed(tuple(evidence.items()))))

        self.assertEqual(first, second)
        self.assertEqual(first["result"], "skipped")

        mixed = build_suite_summary(
            expectations,
            {
                "service-access": {"status": "passed"},
                "swagger": {"status": "skipped"},
            },
        )
        self.assertEqual(mixed["result"], "passed")

    def test_live_e2e_evidence_target_is_local_and_ignored(self) -> None:
        _assert_evidence_target(self)

    def test_blank_success_page_on_expected_route_is_browser_reachable(self) -> None:
        self.assertTrue(
            _browser_navigation_reached_expected_host(
                "https://swagger.tsw.local/status",
                "https://swagger.tsw.local",
            )
        )

    def test_browser_network_error_page_is_not_reachable(self) -> None:
        self.assertFalse(
            _browser_navigation_reached_expected_host(
                "about:neterror?e=dnsNotFound",
                "https://pulsar-api.tsw.local/admin/v2/clusters",
            )
        )

    def test_browser_result_evidence_is_redacted(self) -> None:
        evidence = BrowserRouteResult(
            route_name="service-access",
            url="https://service-access.tsw.local",
            result="blocked",
            redacted_reason="live_consent_missing",
        ).to_evidence()

        self.assertEqual(evidence["route_name"], "service-access")
        self.assertNotIn("password", repr(evidence).casefold())
        self.assertNotIn("secret", repr(evidence).casefold())
        self.assertNotIn("token", repr(evidence).casefold())

    def test_browser_result_writer_creates_route_and_suite_evidence(self) -> None:
        result = BrowserRouteResult(
            route_name="service-access",
            url="https://service-access.tsw.local",
            result="skipped",
            redacted_reason="blocked_missing_credential_source",
        )

        expectation = BrowserRouteExpectation(
            "service-access",
            "https://service-access.tsw.local",
        )
        with TemporaryDirectory() as temporary_directory:
            evidence_root = Path(temporary_directory)
            with patch(f"{__name__}.E2E_EVIDENCE_ROOT", evidence_root):
                route_path = _record_route_result(result, (expectation,))
                route_evidence = json.loads(route_path.read_text(encoding="utf-8"))
                suite_evidence = json.loads(
                    (evidence_root / "suite-summary.json").read_text(encoding="utf-8")
                )

        self.assertEqual(evidence_root / "service-access.json", route_path)
        self.assertEqual(route_evidence["status"], "skipped")
        self.assertIn("service-access", suite_evidence["status_matrix"]["skipped"])

    def test_missing_consent_skip_does_not_replace_existing_live_pass_evidence(self) -> None:
        expectation = BrowserRouteExpectation(
            "service-access",
            "https://service-access.tsw.local",
        )
        passed = BrowserRouteResult(
            route_name="service-access",
            url=expectation.dashboard_url,
            result="passed",
        )
        missing_consent = BrowserRouteResult(
            route_name="service-access",
            url=expectation.dashboard_url,
            result="skipped",
            redacted_reason="blocked_live_consent_missing",
        )

        with TemporaryDirectory() as temporary_directory:
            evidence_root = Path(temporary_directory)
            with patch(f"{__name__}.E2E_EVIDENCE_ROOT", evidence_root):
                live_path = _record_route_result(passed, (expectation,))
                skip_path = _record_route_result(missing_consent, (expectation,))
                live_evidence = json.loads(live_path.read_text(encoding="utf-8"))
                live_summary = json.loads(
                    (evidence_root / "suite-summary.json").read_text(encoding="utf-8")
                )
                skip_summary = json.loads(
                    (evidence_root / "non-live-consent" / "suite-summary.json").read_text(
                        encoding="utf-8"
                    )
                )

        self.assertEqual(evidence_root / "service-access.json", live_path)
        self.assertEqual(
            evidence_root / "non-live-consent" / "service-access.json",
            skip_path,
        )
        self.assertEqual(live_evidence["status"], "passed")
        self.assertEqual(live_summary["result"], "passed")
        self.assertEqual(skip_summary["result"], "skipped")


def _assert_routed_https_url(testcase: Any, url: str) -> None:
    parsed = urlparse(url)
    testcase.assertEqual("https", parsed.scheme)
    testcase.assertTrue(parsed.hostname and parsed.hostname.endswith(".tsw.local"))
    testcase.assertIsNone(parsed.port)
    testcase.assertFalse(parsed.username)
    testcase.assertFalse(parsed.password)
    testcase.assertFalse(parsed.query)
    testcase.assertFalse(parsed.fragment)


def _browser_navigation_reached_expected_host(current_url: str, expected_url: str) -> bool:
    current = urlparse(current_url)
    expected = urlparse(expected_url)
    return (
        current.scheme == "https"
        and current.hostname is not None
        and current.hostname == expected.hostname
    )


def _assert_evidence_target(testcase: Any) -> None:
    if live_e2e_enabled():
        testcase.assertTrue(live_browser_evidence_root().is_absolute())
        return
    testcase.assertEqual(
        ".tiny-swarm-world/evidence/classic-public-beta-rc1",
        E2E_EVIDENCE_ROOT.as_posix(),
    )


def _record_route_result(
    result: BrowserRouteResult,
    expectations: Sequence[BrowserRouteExpectation] | None = None,
) -> Path:
    evidence_root = live_browser_evidence_root() if live_e2e_enabled() else E2E_EVIDENCE_ROOT
    if (
        result.result == "skipped"
        and result.redacted_reason == "blocked_live_consent_missing"
    ):
        evidence_root /= "non-live-consent"
    if live_e2e_enabled():
        ensure_secure_directory(evidence_root)
    else:
        evidence_root.mkdir(parents=True, exist_ok=True)
    route_path = evidence_root / f"{result.route_name}.json"
    route_path.write_text(
        json.dumps(result.to_evidence(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_suite_summary(expectations, evidence_root=evidence_root)
    return route_path


def build_suite_summary(
    expectations: Sequence[BrowserRouteExpectation],
    route_evidence: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    expected_by_name: dict[str, BrowserRouteExpectation] = {}
    for expectation in expectations:
        if expectation.route_name in expected_by_name:
            raise AssertionError(
                f"duplicate browser route expectation: {expectation.route_name}"
            )
        expected_by_name[expectation.route_name] = expectation

    status_matrix: dict[str, list[str]] = {status: [] for status in SUITE_STATUSES}
    route_results: list[dict[str, object]] = []
    for route_name in sorted(expected_by_name):
        expectation = expected_by_name[route_name]
        evidence = route_evidence.get(route_name)
        if evidence is None:
            status = "missing"
            redacted_reason = "missing_route_evidence"
        else:
            status = str(evidence.get("status", evidence.get("result", "failed")))
            raw_reason = evidence.get("redacted_reason", "")
            redacted_reason = raw_reason if isinstance(raw_reason, str) else ""
        if status not in status_matrix:
            status = "failed"
            redacted_reason = "invalid_route_evidence_status"
        status_matrix[status].append(route_name)
        route_results.append(
            BrowserRouteResult(
                route_name=route_name,
                url=expectation.dashboard_url,
                result=status,
                redacted_reason=redacted_reason,
            ).to_evidence()
        )

    if status_matrix["failed"] or status_matrix["missing"]:
        result = "failed"
    elif status_matrix["skipped"] and not status_matrix["passed"]:
        result = "skipped"
    else:
        result = "passed"
    return {
        "evidence_kind": "routed_browser_e2e_suite_summary",
        "result": result,
        "route_results": route_results,
        "status_matrix": status_matrix,
    }


def _write_suite_summary(
    expectations: Sequence[BrowserRouteExpectation] | None = None,
    *,
    evidence_root: Path | None = None,
) -> None:
    selected_evidence_root = evidence_root or E2E_EVIDENCE_ROOT
    selected_expectations = (
        tuple(expectations)
        if expectations is not None
        else browser_route_expectations()
    )
    route_evidence = _read_route_evidence(
        selected_expectations,
        evidence_root=selected_evidence_root,
    )
    suite_summary = build_suite_summary(selected_expectations, route_evidence)
    (selected_evidence_root / "suite-summary.json").write_text(
        json.dumps(suite_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_route_evidence(
    expectations: Sequence[BrowserRouteExpectation],
    *,
    evidence_root: Path | None = None,
) -> dict[str, Mapping[str, object]]:
    selected_evidence_root = evidence_root or E2E_EVIDENCE_ROOT
    route_evidence: dict[str, Mapping[str, object]] = {}
    for expectation in expectations:
        route_path = selected_evidence_root / f"{expectation.route_name}.json"
        if not route_path.is_file():
            continue
        try:
            payload = json.loads(route_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {
                "status": "failed",
                "redacted_reason": "invalid_route_evidence",
            }
        if not isinstance(payload, dict):
            payload = {
                "status": "failed",
                "redacted_reason": "invalid_route_evidence",
            }
        route_evidence[expectation.route_name] = cast(dict[str, object], payload)
    return route_evidence


def _redacted_failure_reason(exc: Exception) -> str:
    reason = exc.__class__.__name__
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    if message:
        reason = f"{reason}: {message[:160]}"
    redacted = re.sub(
        r"(?i)(password|secret|token|bearer|basic)[^,\s;)]*",
        "[redacted]",
        reason,
    )
    redacted = re.sub(r"https?://[^\s]+", "[redacted-url]", redacted)
    redacted = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[redacted-ip]", redacted)
    redacted = re.sub(r"(?i)(?:/[a-z0-9_.-]+){2,}", "[redacted-path]", redacted)
    redacted = re.sub(r"(?i)[a-z]:\\[^\s]+", "[redacted-path]", redacted)
    return redacted[:180]


def _approved_credential(route_name: str) -> tuple[str, str] | None:
    credentials = {
        "infisical": (
            os.environ.get("TSW_INFISICAL_LOGIN_EMAIL", ""),
            os.environ.get("TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD", ""),
        ),
        "jenkins": ("admin", os.environ.get("TSW_JENKINS_ADMIN_PASSWORD", "")),
        "nexus": ("admin", os.environ.get("TSW_NEXUS_ADMIN_PASSWORD", "")),
        "portainer": ("admin", os.environ.get("TSW_PORTAINER_ADMIN_PASSWORD", "")),
        "pulsar-manager": (
            "admin",
            os.environ.get("TSW_PULSAR_MANAGER_ADMIN_PASSWORD", ""),
        ),
        "sonarqube": ("admin", os.environ.get("TSW_SONARQUBE_ADMIN_PASSWORD", "")),
    }
    username, password = credentials.get(route_name, ("", ""))
    if username and password:
        return username, password
    return None


def _perform_login_flow(driver: Any, by: Any, route_name: str, credential: tuple[str, str]) -> None:
    username, password = credential
    body_text, title = _page_text_and_title(driver, by)
    if _post_login_success(route_name, body_text, title):
        return
    username_field = _first_present(
        driver,
        by,
        (
            "input[name='login']",
            "input[id='login-input']",
            "input[name='username']",
            "input[name='user']",
            "input[name='j_username']",
            "input[name='email']",
            "input[type='email']",
            "input[id*='user']",
        ),
    )
    password_field = _first_present(
        driver,
        by,
        (
            "input[name='password']",
            "input[name='j_password']",
            "input[type='password']",
            "input[id*='password']",
        ),
    )
    username_field.clear()
    username_field.send_keys(username)
    password_field.clear()
    password_field.send_keys(password)
    submit = _first_present(
        driver,
        by,
        (
            "button[type='submit']",
            "input[type='submit']",
            "button[name='Submit']",
            "button",
        ),
    )
    submit.click()


def _page_text_and_title(
    driver: Any,
    by: Any,
    *,
    attempts: int = 40,
    retry_interval_seconds: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[str, str]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            body = driver.find_element(by.TAG_NAME, "body")
            return str(body.text), str(driver.title)
        except Exception as exc:
            last_error = exc
        if attempt + 1 < attempts:
            sleep(retry_interval_seconds)
    raise AssertionError("expected a stable browser document body") from last_error


def _wait_for_post_login_success(
    driver: Any,
    by: Any,
    route_name: str,
    *,
    attempts: int = 40,
    retry_interval_seconds: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[str, str]:
    latest = ("", "")
    for attempt in range(attempts):
        try:
            latest = _page_text_and_title(driver, by, attempts=1)
        except AssertionError:
            latest = ("", "")
        if _post_login_success(route_name, *latest):
            return latest
        if attempt + 1 < attempts:
            sleep(retry_interval_seconds)
    return latest


def _first_present(
    driver: Any,
    by: Any,
    selectors: tuple[str, ...],
    *,
    attempts: int = 40,
    retry_interval_seconds: float = 0.25,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        for selector in selectors:
            try:
                return driver.find_element(by.CSS_SELECTOR, selector)
            except Exception as exc:
                last_error = exc
        if attempt + 1 < attempts:
            sleep(retry_interval_seconds)
    raise AssertionError(f"expected one selector to be present: {selectors}") from last_error


def _post_login_success(route_name: str, body_text: str, title: str) -> bool:
    text = f"{title}\n{body_text}".casefold()
    markers = {
        "infisical": ("projects",),
        "jenkins": ("dashboard", "new item", "manage jenkins"),
        "nexus": ("browse", "repositories"),
        "portainer": ("home", "dashboard", "environments"),
        "pulsar-manager": ("environment", "tenant", "namespace"),
        "sonarqube": ("projects", "issues", "rules", "quality gates"),
    }
    return any(marker in text for marker in markers.get(route_name, (route_name,)))
