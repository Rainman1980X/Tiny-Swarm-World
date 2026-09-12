"""Offline fail-closed checks for the explicit live entrypoint."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from tests.e2e.classic import run_authenticated_acceptance_live as runner
from tests.e2e.classic.browser_e2e_contract import BrowserRouteExpectation


class TestAuthenticatedAcceptanceRunner(unittest.TestCase):
    def test_missing_consent_never_reaches_storage_or_credentials(self) -> None:
        with patch("sys.argv", ["runner", "--phase", "baseline"]), \
             patch.object(runner, "live_browser_evidence_root") as root, \
             redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runner.main()
        root.assert_not_called()

    def test_skipped_or_empty_unittest_suite_is_not_success(self) -> None:
        class Skipped(unittest.TestCase):
            @unittest.skip("offline fixture")
            def test_fixture(self) -> None:
                pass
        self.assertFalse(runner.run_suite(unittest.TestSuite())["passed"])
        self.assertFalse(runner.run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Skipped))["passed"])

    def test_failure_diagnostics_record_type_without_exception_text(self) -> None:
        class Failed(unittest.TestCase):
            def test_synthetic_failure(self) -> None:
                raise AssertionError("synthetic-secret-in-exception")

        result = runner.run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Failed))
        self.assertEqual(["AssertionError"], result["failure_types"])
        self.assertNotIn("synthetic-secret-in-exception", json.dumps(result))

    def test_unqualified_source_never_loads_credentials_or_runs_checks(self) -> None:
        with TemporaryDirectory() as temporary, ExitStack() as stack:
            source = Path(temporary) / "operator.env"
            source.write_text("TEST_FIXTURE=unused\n")
            source.chmod(0o644)
            stack.enter_context(patch.dict("os.environ", {}, clear=True))
            stack.enter_context(patch("sys.argv", ["runner", "--approve-live", "--phase", "baseline", "--env-file", str(source)]))
            stack.enter_context(patch.object(runner, "live_browser_evidence_root", return_value=Path(temporary)))
            bootstrap = stack.enter_context(patch.object(runner, "_prepare_bootstrap_environment"))
            checks = stack.enter_context(patch.object(runner, "run_suite"))
            stack.enter_context(redirect_stderr(io.StringIO()))
            with self.assertRaises(SystemExit):
                runner.main()
            bootstrap.assert_not_called()
            checks.assert_not_called()

    def invoke(self, *, empty: bool = False, api_passed: bool = True, dirty: bool = False,
               readiness_count: int | None = 8) -> dict[str, object]:
        with TemporaryDirectory() as temporary, ExitStack() as stack:
            stack.enter_context(patch.dict("os.environ", {}, clear=True))
            stack.enter_context(patch("sys.argv", ["runner", "--approve-live", "--phase", "baseline"]))
            stack.enter_context(patch.object(runner, "live_browser_evidence_root", return_value=Path(temporary)))
            stack.enter_context(patch.object(runner, "_prepare_bootstrap_environment", return_value={}))
            stack.enter_context(patch.object(runner.subprocess, "check_output", side_effect=["a" * 40, "changed" if dirty else ""]))
            # Synthetic summaries preserve the real suite cardinalities.
            def suite_result(suite):
                count = 1 if suite.countTestCases() == 1 else readiness_count
                return {"tests": count, "passed": True, "failures": [], "errors": [],
                        "skipped": [], "failure_types": [], "duration_seconds": 0.1}
            stack.enter_context(patch.object(runner, "run_suite", side_effect=suite_result))
            stack.enter_context(patch.object(runner, "browser_route_expectations", return_value=() if empty else (
                BrowserRouteExpectation("jenkins", "https://jenkins.tsw.local", True, "admin", "platform/jenkins"),
            )))
            stack.enter_context(patch.object(runner, "_approved_credential", return_value=("admin", "fixture")))
            stack.enter_context(patch.object(runner, "probe_authentication", return_value={
                "authenticated_access_verified": api_passed, "invalid_rejected": api_passed,
                "redacted_failure_reason": "" if api_passed else "identity_not_verified",
            }))
            stack.enter_context(patch(
                "tests.e2e.classic.test_post_install_browser_live.LivePostInstallConfig.from_environment",
                return_value=Mock(tls_ca_bundle="/fixture-ca.pem"),
            ))
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            code = runner.main()
            report = json.loads(next(Path(temporary).glob("*/result.json")).read_text())
            self.assertEqual(code, report["exit_code"])
            terminal = json.loads(output.getvalue().splitlines()[-1])
            report["terminal"] = terminal
            return report

    def test_empty_inventory_cannot_be_live_verified(self) -> None:
        self.assertNotEqual(self.invoke(empty=True)["status"], "LIVE_VERIFIED")

    def test_failed_authenticated_operation_cannot_be_live_verified(self) -> None:
        self.assertNotEqual(self.invoke(api_passed=False)["status"], "LIVE_VERIFIED")

    def test_dirty_revision_cannot_be_live_verified(self) -> None:
        self.assertNotEqual(self.invoke(dirty=True)["status"], "LIVE_VERIFIED")

    def test_qualified_complete_phase_records_revision_and_inventory(self) -> None:
        report = self.invoke()
        self.assertEqual(report["status"], "LIVE_VERIFIED")
        self.assertEqual(report["revision"], "a" * 40)
        self.assertTrue(report["inventory"])

    def test_terminal_summary_counts_live_readiness_browser_and_api_checks(self) -> None:
        terminal = self.invoke()["terminal"]
        assert isinstance(terminal, dict)
        summary = terminal["acceptance_summary"]
        self.assertTrue(summary["passed"])
        self.assertEqual(8, summary["readiness_before_tests"])
        self.assertEqual(8, summary["readiness_after_tests"])
        self.assertEqual(1, summary["expected_browser_tests"])
        self.assertEqual(1, summary["browser_tests"])
        self.assertEqual(1, summary["expected_api_checks"])
        self.assertEqual(1, summary["api_checks"])
        self.assertEqual(17, summary["live_tests"])

    def test_readiness_missing_or_wrong_count_cannot_be_live_verified(self) -> None:
        for count in (None, 0, 7, 9, 37):
            with self.subTest(count=count):
                report = self.invoke(readiness_count=count)
                self.assertEqual("LIVE_PARTIAL", report["status"])
                terminal = report["terminal"]
                assert isinstance(terminal, dict)
                self.assertFalse(terminal["acceptance_summary"]["passed"])
