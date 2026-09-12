from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.live import run_classic_acceptance
from tools.live.secure_runtime_paths import (
    NATIVE_LINUX,
    WINDOWS_MOUNTED,
    assess_secret_file,
    classify_path,
    ensure_secure_directory,
)


class TestSecureRuntimePaths(unittest.TestCase):
    def test_drvfs_path_is_rejected_even_when_stat_reports_0600(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = root / "storage"
            storage.mkdir()
            storage.chmod(0o700)
            secret = storage / "live.env"
            secret.write_text("TSW_TEST_SECRET=not-written-to-evidence\n", encoding="utf-8")
            secret.chmod(0o600)

            assessment = assess_secret_file(
                secret,
                host="wsl2",
                mountinfo_reader=lambda: _mountinfo(root, "9p", "drvfs"),
            )

        self.assertEqual(WINDOWS_MOUNTED, assessment.filesystem_classification)
        self.assertFalse(assessment.allowed)
        self.assertIn("filesystem_not_linux_native", assessment.reasons())

    def test_wsl_native_path_is_accepted_when_owner_and_modes_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            storage = root / "storage"
            storage.mkdir()
            storage.chmod(0o700)
            secret = storage / "live.env"
            secret.write_text("TSW_TEST_SECRET=not-written-to-evidence\n", encoding="utf-8")
            secret.chmod(0o600)

            assessment = assess_secret_file(
                secret,
                host="wsl2",
                mountinfo_reader=lambda: _mountinfo(root, "ext4", "/dev/vda"),
            )

        self.assertEqual("wsl_linux", assessment.filesystem_classification)
        self.assertTrue(assessment.allowed)
        self.assertEqual("true", assessment.to_safe_dict()["accepted"])

    def test_native_host_classifies_without_reading_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.env"
            self.assertEqual(NATIVE_LINUX, classify_path(path, host="native_linux"))

    def test_existing_non_private_evidence_directory_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence"
            evidence.mkdir(mode=0o755)

            with self.assertRaises(RuntimeError):
                ensure_secure_directory(evidence)

            self.assertEqual(0o755, evidence.stat().st_mode & 0o777)

    def test_new_evidence_directory_is_created_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "nested" / "evidence"

            assessment = ensure_secure_directory(evidence)

            self.assertTrue(assessment.allowed)
            self.assertEqual(0o700, evidence.stat().st_mode & 0o777)

    def test_e2e_summary_does_not_propagate_secret_like_output(self) -> None:
        secret = "previously-exposed-value"
        summary = run_classic_acceptance._summarize(
            "classic_e2e",
            f"FAILED: {secret}\n",
            "",
        )

        self.assertNotIn(secret, repr(summary))
        self.assertEqual("failed", summary["result"])

    def test_skipped_e2e_is_not_a_success(self) -> None:
        result = run_classic_acceptance.CommandResult(
            operation="classic_e2e",
            started_at="now",
            finished_at="now",
            duration_seconds=0.1,
            exit_code=0,
            summary=run_classic_acceptance._summarize(
                "classic_e2e",
                "Ran 1 test in 0.1s\nOK (skipped=1)\n",
                "",
            ),
        )

        self.assertFalse(run_classic_acceptance._operation_succeeded(result))
        self.assertFalse(run_classic_acceptance._valid_rotation_reference("raw secret"))
        self.assertTrue(run_classic_acceptance._valid_rotation_reference("ticket-271-20260829"))

    def test_disposable_test_profile_does_not_require_rotation_reference(self) -> None:
        self.assertTrue(run_classic_acceptance._rotation_reference_valid_for_profile(True, None))
        self.assertFalse(run_classic_acceptance._rotation_reference_valid_for_profile(False, None))
        self.assertEqual(
            "not_applicable_test_only",
            run_classic_acceptance._rotation_evidence_status(True, "ignored-reference"),
        )
        self.assertEqual(
            "recorded",
            run_classic_acceptance._rotation_evidence_status(False, "ticket-271-20260829"),
        )

    def test_structured_summary_accepts_runner_status_lines_before_json(self) -> None:
        payload = run_classic_acceptance._find_structured_payload(
            "setup phase started\n{\n  \"status\": \"completed\"\n}\n",
            "",
        )

        self.assertEqual({"status": "completed"}, payload)

    def test_structured_summary_keeps_diagnostics_redacted_and_bounded(self) -> None:
        summary = run_classic_acceptance._summarize(
            "setup",
            "{\"status\": \"failed\", \"message\": \"password=secret-value\", "
            "\"phase_results\": [{\"name\": \"setup\", \"status\": \"failed\"}]}\n",
            "",
        )

        self.assertEqual("failed", summary["result"])
        self.assertEqual("password=<redacted>", summary["message"])
        self.assertEqual(
            {"count": 1, "failed": [{"name": "setup"}]},
            summary["phase_results"],
        )


def _mountinfo(root: Path, filesystem_type: str, source: str) -> str:
    return (
        f"36 25 0:36 / {root} rw,relatime - {filesystem_type} {source} rw\n"
    )


if __name__ == "__main__":
    unittest.main()
