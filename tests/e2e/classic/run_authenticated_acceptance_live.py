"""Run existing Classic acceptance on one approved host and lifecycle phase."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import io
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
import unittest
from urllib.parse import urlsplit

from tiny_swarm_world.simple_installer import _prepare_bootstrap_environment
from tests.e2e.classic.authenticated_service_contract import probe_authentication
from tests.e2e.classic.browser_e2e_contract import (
    BrowserRouteE2EContract, _approved_credential,
    browser_route_expectations, live_browser_evidence_root,
)
from tools.live.secure_runtime_paths import (
    assess_secret_file, ensure_secure_directory, host_classification,
)
from tools.live.run_classic_acceptance import EXPECTED_READINESS_TESTS, SAFE_FAILURE_TYPES


class _TypedFailureResult(unittest.TextTestResult):
    """Keep exception categories, never exception messages or tracebacks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failure_types: set[str] = set()

    def _record_type(self, err) -> None:
        name = err[0].__name__
        self.failure_types.add(name if name in SAFE_FAILURE_TYPES else "OtherError")

    def addError(self, test, err) -> None:
        self._record_type(err)
        super().addError(test, err)

    def addFailure(self, test, err) -> None:
        self._record_type(err)
        super().addFailure(test, err)

    def addSubTest(self, test, subtest, err) -> None:
        if err is not None:
            self._record_type(err)
        super().addSubTest(test, subtest, err)


def run_suite(suite: unittest.TestSuite) -> dict[str, object]:
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=_TypedFailureResult).run(suite)
    assert isinstance(result, _TypedFailureResult)
    return {
        "tests": result.testsRun,
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "skipped": [test.id() for test, _ in result.skipped],
        "failure_types": sorted(result.failure_types),
        "passed": result.testsRun > 0 and result.wasSuccessful() and not result.skipped,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def _suite_passed(result: dict[str, Any], expected_tests: int) -> bool:
    return (
        expected_tests > 0 and type(result.get("tests")) is int
        and result["tests"] == expected_tests and result.get("passed") is True
        and all(result.get(key) == [] for key in ("failures", "errors", "skipped"))
    )


def _acceptance_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Count actual observations against the effective model's required inventory."""
    before = report.get("readiness_before", {})
    after = report.get("readiness_after", {})
    inventory = report.get("inventory", [])
    entries = report.get("routes", [])
    expected_routes = [item["route"] for item in inventory]
    expected_api = {item["route"] for item in inventory if item["api_authentication_required"]}
    observed_routes = [item["route"] for item in entries]
    suites = [before, after, *(item["browser"] for item in entries)]

    def tests(result):
        value = result.get("tests")
        return value if type(value) is int and value >= 0 else 0

    api_checks = sum(
        item["route"] in expected_api
        and item.get("api", {}).get("authenticated_access_verified") is True
        and item.get("api", {}).get("invalid_rejected") is True
        for item in entries
    )
    passed = (
        report.get("dirty_checkout") is False
        and _suite_passed(before, EXPECTED_READINESS_TESTS)
        and _suite_passed(after, EXPECTED_READINESS_TESTS)
        and bool(expected_routes) and bool(expected_api)
        and len(set(expected_routes)) == len(expected_routes)
        and observed_routes == expected_routes
        and all(_suite_passed(item["browser"], 1) for item in entries)
        and api_checks == len(expected_api)
    )
    return {
        "schema": "classic_authenticated_acceptance_v1",
        "readiness_before_tests": tests(before), "readiness_after_tests": tests(after),
        "expected_browser_tests": len(expected_routes),
        "browser_tests": sum(tests(item["browser"]) for item in entries),
        "expected_api_checks": len(expected_api), "api_checks": api_checks,
        "live_tests": sum(tests(item) for item in suites),
        **{key: sum(len(item.get(key, [])) for item in suites)
           for key in ("failures", "errors", "skipped")},
        "failure_types": sorted({name for item in suites for name in item.get("failure_types", [])
                                 if name in SAFE_FAILURE_TYPES}),
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-live", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--phase", choices=("baseline", "post-restart"), required=True)
    args = parser.parse_args()
    if not args.approve_live:
        parser.error("--approve-live is required")
    # Qualify storage before loading credentials or constructing any browser.
    root = live_browser_evidence_root()
    started_at = datetime.now(UTC)
    run = root / (args.phase + "-" + started_at.strftime("%Y%m%dT%H%M%S%fZ"))
    ensure_secure_directory(run)
    os.environ["TSW_RUN_POST_INSTALL_BROWSER_LIVE"] = "1"
    from tests.e2e.classic.test_post_install_browser_live import (
        LivePostInstallConfig, _load_shell_environment,
    )
    environment = dict(os.environ)
    if args.env_file:
        if not assess_secret_file(args.env_file, host=host_classification()).allowed:
            parser.error("protected environment file qualification failed")
        environment.update(_load_shell_environment(args.env_file))
        environment["TSW_LIVE_INSTALLATION_ENV"] = str(args.env_file)
        environment["TSW_INSTALL_ENV_FILE"] = str(args.env_file)
    else:
        selected = Path(environment.get("TSW_LIVE_INSTALLATION_ENV", ".tiny-swarm-world/local/live-installation.env"))
        if selected.exists() and not assess_secret_file(selected, host=host_classification()).allowed:
            parser.error("default environment file qualification failed")
    environment = _prepare_bootstrap_environment(environment, Path.cwd())
    environment.update(TSW_RUN_POST_INSTALL_BROWSER_LIVE="1", TSW_LIVE_EVIDENCE_ROOT=str(run))
    os.environ.update(environment)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    report: dict[str, object] = {
        "revision": revision, "dirty_checkout": dirty,
        "host": host_classification(), "profile": "service-access",
        "phase": args.phase, "started_at_utc": started_at.isoformat(),
        "consent": "explicit_operator_complete_issue_run",
        "command": "python -m tests.e2e.classic.run_authenticated_acceptance_live --approve-live --phase " + args.phase,
        "storage_qualified_before_browser": True,
        "artifacts": "value-free JSON only; screenshots, traces and raw runner output excluded",
        "restart": "externally orchestrated; this phase alone does not prove task replacement",
        "cleanup": "browser sessions closed; no service configuration or credential changes",
    }
    all_passed = not dirty
    try:
        readiness = run_suite(unittest.defaultTestLoader.loadTestsFromName(
            "tests.e2e.classic.test_post_install_browser_live.PostInstallBrowserLiveTest",
        ))
        report["readiness_before"] = readiness
        if not _suite_passed(readiness, EXPECTED_READINESS_TESTS):
            raise RuntimeError("readiness_failed")
        config = LivePostInstallConfig.from_environment()
        expectations = browser_route_expectations()
        if not expectations:
            raise RuntimeError("empty_required_inventory")
        report["inventory"] = [
            {
                "route": item.route_name,
                "ui_login_required": item.credential_required and item.route_name != "pulsar-admin-api",
                "api_authentication_required": item.credential_required,
                "principal": "configured_login_email" if item.route_name == "infisical" else item.principal_label,
                "credential_reference": item.credential_reference,
                "failure_signal": "explicit_invalid_login_rejection_and_failed_authenticated_access",
            }
            for item in expectations
        ]
        entries: list[dict[str, object]] = []
        report["routes"] = entries
        for expectation in expectations:
            route = expectation.route_name
            testcase = type("SelectedClassicRoute", (BrowserRouteE2EContract, unittest.TestCase), {
                "route_name": route,
            })
            result = run_suite(unittest.TestSuite([
                testcase("test_live_routed_link_opens_with_selenium"),
            ]))
            entry: dict[str, object] = {"route": route, "browser": result}
            entries.append(entry)
            all_passed = all_passed and _suite_passed(result, 1)
            if expectation.credential_required:
                credential = (
                    ("admin", config.pulsar_admin_token or "") if route == "pulsar-admin-api"
                    else _approved_credential(route)
                )
                if credential is None:
                    raise RuntimeError("required_credential_unavailable")
                url = urlsplit(expectation.dashboard_url)
                api = probe_authentication(route, f"{url.scheme}://{url.netloc}",
                                           *credential, verify=config.tls_ca_bundle or True)
                entry["api"] = dict(api)
                all_passed = all_passed and api["authenticated_access_verified"] and api["invalid_rejected"]
            print(json.dumps(entry, sort_keys=True), flush=True)
        after = run_suite(unittest.defaultTestLoader.loadTestsFromName(
            "tests.e2e.classic.test_post_install_browser_live.PostInstallBrowserLiveTest",
        ))
        report["readiness_after"] = after
        all_passed = all_passed and _suite_passed(after, EXPECTED_READINESS_TESTS)
    except Exception as exc:
        all_passed = False
        report["failure_type"] = type(exc).__name__
    finished = datetime.now(UTC)
    summary = _acceptance_summary(report)
    all_passed = all_passed and summary["passed"]
    summary["passed"] = all_passed
    report.update(
        finished_at_utc=finished.isoformat(),
        duration_seconds=round((finished - started_at).total_seconds(), 3),
        exit_code=0 if all_passed else 1,
        status="LIVE_VERIFIED" if all_passed else "LIVE_PARTIAL",
        acceptance_summary=summary,
    )
    path = run / "result.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)
    print(json.dumps({"status": report["status"], "report": str(path),
                      "acceptance_summary": summary}), flush=True)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
