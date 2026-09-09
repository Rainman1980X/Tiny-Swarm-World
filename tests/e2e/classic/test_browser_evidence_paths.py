"""Verify browser evidence storage without contacting live services."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests.e2e.classic import browser_e2e_contract as browser
from tests.e2e.classic.test_post_install_browser_live import _EvidenceRecorder


class BrowserEvidencePathsTest(unittest.TestCase):
    def test_live_root_precedes_legacy_root_and_keeps_existing_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "protected"
            root.mkdir(mode=0o700)
            previous = root / "previous.json"
            previous.write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {
                "TSW_LIVE_EVIDENCE_ROOT": str(root),
                "TSW_CLASSIC_EVIDENCE_ROOT": str(root / "unused"),
                browser.RUN_LIVE_ENV: "1",
            }, clear=True):
                result = browser.BrowserRouteResult(
                    "service-access", "https://service-access.tsw.local", "passed"
                )
                path = browser._record_route_result(result, (
                    browser.BrowserRouteExpectation(result.route_name, result.url),
                ))
            self.assertEqual(path.parent, root)
            self.assertEqual(json.loads(path.read_text())["status"], "passed")
            self.assertEqual(previous.read_text(), "{}")
            self.assertFalse((root / "unused").exists())
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)

    def test_legacy_override_and_xdg_default_resolve_to_private_storage(self) -> None:
        with TemporaryDirectory() as directory:
            base = Path(directory)
            for environment, expected in (
                ({"TSW_CLASSIC_EVIDENCE_ROOT": str(base / "legacy")}, base / "legacy"),
                ({"XDG_STATE_HOME": str(base)},
                 base / "tiny-swarm-world/evidence/classic-public-beta-rc1"),
            ):
                with self.subTest(environment=environment), patch.dict(
                    os.environ, environment, clear=True
                ):
                    self.assertEqual(browser.live_browser_evidence_root(), expected)
                    self.assertEqual(expected.stat().st_mode & 0o777, 0o700)

    def test_insecure_existing_root_is_rejected_without_writing_results(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "public"
            root.mkdir(mode=0o755)
            with patch.dict(os.environ, {
                "TSW_LIVE_EVIDENCE_ROOT": str(root), browser.RUN_LIVE_ENV: "1",
            }, clear=True):
                with self.assertRaises(RuntimeError):
                    browser._record_route_result(browser.BrowserRouteResult(
                        "service-access", "https://service-access.tsw.local", "passed"
                    ))
                with self.assertRaises(RuntimeError):
                    _EvidenceRecorder(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_windows_filesystem_is_rejected_before_directory_creation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "blocked"
            with patch.dict(os.environ, {"TSW_LIVE_EVIDENCE_ROOT": str(root)}, clear=True):
                with patch("tools.live.secure_runtime_paths.classify_path",
                           return_value="windows_mounted"):
                    with self.assertRaises(RuntimeError):
                        browser.live_browser_evidence_root()
            self.assertFalse(root.exists())

    def test_post_install_recorder_protects_root_and_run_directory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "protected"
            recorder = _EvidenceRecorder(root)
            recorder.record("readiness", {"result": "passed"})
            recorder.write()
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(recorder.path.stat().st_mode & 0o777, 0o700)
            payload = json.loads((recorder.path / "summary.json").read_text())
            self.assertEqual(payload["records"][0]["result"], "passed")
