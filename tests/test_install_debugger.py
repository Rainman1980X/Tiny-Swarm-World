import importlib.util
import stat
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALL_DEBUGGER_PATH = REPOSITORY_ROOT / "tools" / "install_debugger.py"


def _load_install_debugger():
    spec = importlib.util.spec_from_file_location("install_debugger", INSTALL_DEBUGGER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["install_debugger"] = module
    spec.loader.exec_module(module)
    return module


install_debugger = _load_install_debugger()


class TestInstallDebugger(unittest.TestCase):
    def test_diagnose_reports_install_script_contract_and_missing_execute_bit(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            install_script = root / "install.sh"
            install_script.write_text(_install_script_text(), encoding="utf-8")
            install_script.chmod(0o644)

            findings = install_debugger.diagnose(root)

        findings_by_title = {finding.title: finding for finding in findings}
        self.assertEqual(findings_by_title["install.sh Python installer entry point"].status, "OK")
        self.assertEqual(findings_by_title["install.sh source checkout Python path"].status, "OK")
        self.assertEqual(findings_by_title["install.sh executable"].status, "FAIL")

    def test_live_fix_permissions_repairs_install_script_and_secret_mode(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            install_script = root / "install.sh"
            install_script.write_text(_install_script_text(), encoding="utf-8")
            install_script.chmod(0o644)
            secret_file = root / ".tiny-swarm-world" / "local" / "live-installation.env"
            secret_file.parent.mkdir(parents=True)
            secret_file.write_text("export TSW_PORTAINER_ADMIN_PASSWORD='value'\n", encoding="utf-8")
            secret_file.chmod(0o644)

            findings = install_debugger.diagnose(root, live=True, fix_permissions=True)

            install_mode = stat.S_IMODE(install_script.stat().st_mode)
            secret_mode = stat.S_IMODE(secret_file.stat().st_mode)

        self.assertTrue(install_mode & stat.S_IXUSR)
        self.assertEqual(secret_mode, 0o600)
        self.assertIn("FIXED", {finding.status for finding in findings})

    def test_fix_permissions_requires_live_mode(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))

            findings = install_debugger.diagnose(root, fix_permissions=True)

        self.assertEqual(findings[0].status, "FAIL")
        self.assertIn("--fix-permissions requires --live", findings[0].detail)

    def test_service_definition_reports_wsl_systemd_and_windows_command_issues(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            unit = root / "infra" / "systemd" / "bad.service"
            unit.parent.mkdir(parents=True)
            unit.write_text(
                "\n".join(
                    (
                        "[Unit]",
                        "After=network-online.target",
                        "[Service]",
                        "ExecStart=powershell.exe -File C:\\\\tmp\\\\start.ps1",
                    )
                ),
                encoding="utf-8",
            )
            systemd_state = install_debugger.SystemdState(
                wsl=True,
                available=False,
                pid1="init",
                wsl_conf_systemd="false",
            )

            findings = install_debugger.check_service_definitions(root, systemd_state)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].status, "FAIL")
        self.assertIn("systemd is not available", findings[0].detail)
        self.assertIn("Windows-native command", findings[0].detail)
        self.assertIn("network-online.target", findings[0].detail)

    def test_log_guidance_points_to_latest_evidence_and_service_search(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            older = (
                root / ".tiny-swarm-world" / "evidence" / "installation-tests" / "wsl2"
                / "20260101T000000Z"
            )
            newer = (
                root / ".tiny-swarm-world" / "evidence" / "installation-tests" / "wsl2"
                / "20260201T000000Z"
            )
            older.mkdir(parents=True)
            newer.mkdir(parents=True)
            (newer / "setup-run.log").write_text("Service failed\n", encoding="utf-8")

            guidance = install_debugger.log_guidance(root)

        rendered = "\n".join(guidance)
        self.assertIn("20260201T000000Z", rendered)
        self.assertIn('grep -n -i "service"', rendered)
        self.assertIn("journalctl --no-pager -u '<unit>.service'", rendered)

    def test_log_guidance_points_to_latest_evidence_across_host_directories(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            older = (
                root / ".tiny-swarm-world" / "evidence" / "installation-tests" / "wsl2"
                / "20260101T000000Z"
            )
            newer = (
                root / ".tiny-swarm-world" / "evidence" / "installation-tests"
                / "native_linux" / "20260201T000000Z"
            )
            older.mkdir(parents=True)
            newer.mkdir(parents=True)
            (newer / "setup-run.log").write_text("Service failed\n", encoding="utf-8")

            guidance = install_debugger.log_guidance(root)

        rendered = "\n".join(guidance)
        self.assertIn("installation-tests/native_linux/20260201T000000Z", rendered)

    def test_log_guidance_keeps_legacy_wsl2_evidence_readable(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = _minimal_repo(Path(tempdir))
            legacy = (
                root / ".tiny-swarm-world" / "evidence" / "installation-tests" / "wsl2"
                / "20260101T000000Z"
            )
            legacy.mkdir(parents=True)
            (legacy / "setup-run.log").write_text("Service failed\n", encoding="utf-8")

            guidance = install_debugger.log_guidance(root)

        rendered = "\n".join(guidance)
        self.assertIn("installation-tests/wsl2/20260101T000000Z", rendered)


def _minimal_repo(root: Path) -> Path:
    (root / "src" / "tiny_swarm_world").mkdir(parents=True)
    return root


def _install_script_text() -> str:
    return "\n".join(
        (
            "#!/usr/bin/env bash",
            "set -Eeuo pipefail",
            "installer_module=\"tiny_swarm_world.simple_installer\"",
            "export PYTHONPATH=\"${PYTHONPATH:+$PYTHONPATH:}src\"",
            "exec python3 -m \"$installer_module\" \"$@\"",
        )
    )
