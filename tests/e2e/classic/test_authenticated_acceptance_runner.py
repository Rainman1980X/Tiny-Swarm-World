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

    def invoke(self, *, empty: bool = False, api_passed: bool = True, dirty: bool = False) -> dict[str, object]:
        with TemporaryDirectory() as temporary, ExitStack() as stack:
            stack.enter_context(patch.dict("os.environ", {}, clear=True))
            stack.enter_context(patch("sys.argv", ["runner", "--approve-live", "--phase", "baseline"]))
            stack.enter_context(patch.object(runner, "live_browser_evidence_root", return_value=Path(temporary)))
            stack.enter_context(patch.object(runner, "_prepare_bootstrap_environment", return_value={}))
            stack.enter_context(patch.object(runner.subprocess, "check_output", side_effect=["a" * 40, "changed" if dirty else ""]))
            stack.enter_context(patch.object(runner, "run_suite", return_value={"passed": True}))
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
            stack.enter_context(redirect_stdout(io.StringIO()))
            code = runner.main()
            report = json.loads(next(Path(temporary).glob("*/result.json")).read_text())
            self.assertEqual(code, report["exit_code"])
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
