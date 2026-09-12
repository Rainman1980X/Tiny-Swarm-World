"""Synthetic process results only; no browser or infrastructure is executed."""

from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.live import run_classic_acceptance as runner


def authenticated_payload() -> dict:
    """Explicit synthetic counts for the current nine-route Classic inventory."""
    return {
        "status": "LIVE_VERIFIED",
        "report": "/private/synthetic/result.json",
        "acceptance_summary": {
            "schema": "classic_authenticated_acceptance_v1",
            "readiness_before_tests": 8,
            "readiness_after_tests": 8,
            "expected_browser_tests": 9,
            "browser_tests": 9,
            "expected_api_checks": 7,
            "api_checks": 7,
            "live_tests": 25,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "passed": True,
        },
    }


class TestClassicLiveRunner(unittest.TestCase):
    def test_readiness_requires_exact_positive_live_count_and_terminal_ok(self) -> None:
        outputs = (
            "OK\n", "Ran 0 tests in 0.1s\nOK\n",
            "Ran 7 tests in 0.1s\nOK\n", "Ran 9 tests in 0.1s\nOK\n",
            "Ran 37 tests in 0.1s\nOK\n", "Ran 8 tests in 0.1s\nNOT OK\n",
            "Ran 8 tests in 0.1s\nOK (skipped=1)\n",
            "Ran 8 tests in 0.1s\nOK\nRan 0 tests in 0.1s\nOK\n",
        )
        for output in outputs:
            with self.subTest(output=output):
                self.assertEqual("failed", runner._summarize("classic_e2e", "", output)["result"])
        summary = runner._summarize("classic_e2e", "synthetic log: OK", "Ran 8 tests in 0.1s\nOK\n")
        self.assertEqual("passed", summary["result"])
        self.assertEqual(8, summary["tests"])
        self.assertEqual(8, summary["expected_tests"])

    def test_authentication_uses_terminal_structured_summary_not_progress(self) -> None:
        payload = authenticated_payload()
        summary = runner._summarize("update_authenticated", '{"status":"completed"}\n' + json.dumps(payload), "")
        self.assertEqual("passed", summary["result"])
        self.assertEqual(25, summary["live_tests"])
        self.assertNotIn("/private", repr(summary))

    def test_authentication_rejects_missing_counts_failures_and_inconsistent_success(self) -> None:
        invalid = [{"status": "LIVE_VERIFIED"}, {"status": "completed"}]
        for key, value in (
            ("readiness_before_tests", 0), ("readiness_after_tests", 7),
            ("expected_browser_tests", 0), ("browser_tests", 8),
            ("expected_api_checks", 0), ("api_checks", 6), ("live_tests", 24),
            ("failures", 1), ("errors", 1), ("skipped", 1), ("passed", False),
            ("browser_tests", True), ("schema", "unknown"),
        ):
            payload = authenticated_payload()
            payload["acceptance_summary"][key] = value
            invalid.append(payload)
        for key in authenticated_payload()["acceptance_summary"]:
            payload = authenticated_payload()
            del payload["acceptance_summary"][key]
            invalid.append(payload)
        payload = authenticated_payload()
        payload["status"] = "LIVE_PARTIAL"
        invalid.append(payload)
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual("failed", runner._summarize("update_authenticated", json.dumps(payload), "")["result"])

    def test_authentication_discards_untrusted_details_and_rejects_trailing_noise(self) -> None:
        payload = authenticated_payload()
        payload["acceptance_summary"]["message"] = "synthetic-secret-value"
        payload["acceptance_summary"]["failure_types"] = ["synthetic-secret-value"]
        text = json.dumps(payload)
        self.assertNotIn("synthetic-secret-value", repr(runner._summarize("update_authenticated", text, "")))
        self.assertEqual("failed", runner._summarize("update_authenticated", text + "\nOK\n", "")["result"])
        self.assertEqual("failed", runner._summarize("update_authenticated", "", text)["result"])
        for output in ("", "OK", "[]", "{", " " + "x" * 16_385):
            with self.subTest(length=len(output)):
                self.assertEqual("failed", runner._summarize("update_authenticated", output, "")["result"])

    def test_nonzero_exit_cannot_be_overridden_by_successful_summary(self) -> None:
        result = runner.CommandResult("update_authenticated", "synthetic", "synthetic", 0.1, 1,
                                      runner._summarize("update_authenticated", json.dumps(authenticated_payload()), ""))
        self.assertFalse(runner._operation_succeeded(result))

    def test_typed_workflow_failures_never_become_completed(self) -> None:
        for status in ("failed_to_verify", "failed_to_apply", "failed_to_prepare"):
            with self.subTest(status=status):
                for payload in ({"status": status}, {"status": status, "outcome": {"status": "completed"}}):
                    summary = runner._summarize("setup", json.dumps(payload), "")
                    self.assertEqual(status, summary["result"])

    def test_nested_phase_checks_and_deployment_results_are_bounded_and_value_free(self) -> None:
        failed_check = {"check_id": "SWARM-MANAGER", "status": "failed_to_verify",
                        "message": "synthetic-secret-in-message", "remediation": "synthetic-secret-in-remediation"}
        verification = {"target_id": "deployment:jenkins-stack", "status": "failed_to_verify",
                        "message": "synthetic-secret-in-message", "evidence": {"secret": "synthetic-secret"}}
        payload = {"status": "failed", "phase_results": [{
            "name": "cluster swarm bootstrap", "status": "failed",
            "result": {"checks": [failed_check] * 30, "verification_results": [verification]},
        }]}
        summary = runner._summarize("setup", json.dumps(payload), "")
        phases = summary["phase_results"]
        assert isinstance(phases, dict)
        phase = phases["failed"][0]
        self.assertEqual(20, len(phase["checks"]))
        self.assertEqual({"check_id": "SWARM-MANAGER", "status": "failed_to_verify"}, phase["checks"][0])
        self.assertEqual([{"target_id": "deployment:jenkins-stack", "status": "failed_to_verify"}],
                         phase["verification_results"])
        self.assertNotIn("synthetic-secret", json.dumps(summary))
        top = runner._summarize("update", json.dumps({"status": "failed_to_verify", "verification_results": [verification]}), "")
        self.assertEqual(phase["verification_results"], top["verification_results"])

    def test_later_structured_failure_cannot_be_hidden_by_progress_success(self) -> None:
        summary = runner._summarize("setup", '{"status":"completed"}\n{"status":"failed_to_verify"}\n', "")
        self.assertEqual("failed_to_verify", summary["result"])

    def invoke(self, failure: str | None = None) -> tuple[dict, list]:
        with TemporaryDirectory() as temporary, ExitStack() as stack:
            root = Path(temporary)
            source = root / "synthetic.env"
            source.write_text("SYNTHETIC_FIXTURE=1\n", encoding="utf-8")
            source.chmod(0o600)
            stack.enter_context(patch.dict(os.environ, {}, clear=True))
            stack.enter_context(patch("sys.argv", [
                "runner", "--approve-live", "--test-only", "--env-file", str(source),
                "--evidence-root", str(root / "evidence"), "--update-stack", "jenkins",
                "--update-service", "jenkins", "--update-from-image", "synthetic:1",
                "--update-to-image", "synthetic:2",
            ]))
            stack.enter_context(patch.object(runner, "_git_commit", return_value="a" * 40))
            calls = []

            def operation(name, command, timeout, env_file, environment):
                calls.append((name, command, timeout, env_file, deepcopy(environment)))
                return runner.CommandResult(name, "synthetic", "synthetic", 0.1, 0,
                                            {"result": "failed" if name == failure else "passed"})

            stack.enter_context(patch.object(runner, "_run_operation", side_effect=operation))
            code = runner.main()
            report = json.loads(next((root / "evidence").glob("*/run-summary.json")).read_text())
            self.assertEqual(1 if failure else 0, code)
            return report, calls

    def test_every_phase_has_readiness_then_authentication_and_private_evidence(self) -> None:
        report, calls = self.invoke()
        self.assertEqual("disposable_test", report["execution_profile"])
        self.assertEqual("not_applicable_test_only", report["credential_rotation"]["status"])
        self.assertEqual([
            "diagnostics", "setup", "platform_verify", "classic_e2e", "classic_authenticated",
            "reconcile", "reconcile_e2e", "reconcile_authenticated", "update", "update_e2e",
            "update_authenticated", "recovery", "recovery_e2e", "recovery_authenticated",
        ], [call[0] for call in calls])
        roots = [call[4]["TSW_LIVE_EVIDENCE_ROOT"] for call in calls]
        self.assertEqual(len(calls), len(set(roots)))
        for name, command, _, source, environment in calls:
            self.assertEqual(name, Path(environment["TSW_LIVE_EVIDENCE_ROOT"]).name)
            self.assertEqual(report["run_id"], Path(environment["TSW_LIVE_EVIDENCE_ROOT"]).parent.name)
            self.assertEqual(str(source), environment["TSW_INSTALL_ENV_FILE"])
            self.assertEqual(str(source), environment["TSW_LIVE_INSTALLATION_ENV"])
            if name.endswith("_authenticated"):
                self.assertIn("tests.e2e.classic.run_authenticated_acceptance_live", command)
                self.assertEqual(str(source), command[command.index("--env-file") + 1])

    def test_failed_authentication_stops_before_next_mutation(self) -> None:
        for phase in ("classic", "reconcile", "update", "recovery"):
            name = f"{phase}_authenticated"
            with self.subTest(phase=phase):
                report, calls = self.invoke(failure=name)
                self.assertEqual(name, calls[-1][0])
                self.assertEqual("LIVE_FAILED_AFTER_MUTATION", report["status"])

    def test_operation_pins_storage_after_sourcing_operator_configuration(self) -> None:
        environment = {"TSW_LIVE_EVIDENCE_ROOT": "/synthetic/operation"}
        with patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as process:
            runner._run_operation("diagnostics", ("python3", "fixture.py"), 10,
                                  Path("/synthetic/operator.env"), environment)
        shell = process.call_args.args[0][-1]
        self.assertIn("exec env", shell)
        self.assertIn("TSW_LIVE_EVIDENCE_ROOT=/synthetic/operation", shell)
        self.assertNotIn("synthetic-secret-value", shell)

    def test_operation_uses_approved_runtime_path_without_login_shell_replacement(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "synthetic.env"
            source.write_text("SYNTHETIC_FIXTURE=1\n", encoding="utf-8")
            executable = root / "python3"
            executable.write_text(
                '#!/bin/sh\nprintf \'%s\\n\' \'{"status":"completed","message":"synthetic-runtime"}\'\n',
                encoding="utf-8",
            )
            executable.chmod(0o700)
            environment = {**os.environ, "PATH": str(root) + os.pathsep + os.defpath,
                           "TSW_LIVE_EVIDENCE_ROOT": str(root / "evidence")}
            result = runner._run_operation(
                "diagnostics", ("python3", "-c", 'print(\'{"status":"completed","message":"wrong-runtime"}\')'),
                10, source, environment,
            )
            self.assertEqual(0, result.exit_code)
            self.assertEqual("synthetic-runtime", result.summary["message"])
