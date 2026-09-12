import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tiny_swarm_world.domain.preflight import HostEnvironmentKind
from tiny_swarm_world.infrastructure.adapters.host import HostEnvironmentDetector


class TestHostEnvironmentDetector(unittest.TestCase):
    def test_reads_native_kernel_and_distribution_signals(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/version", "Linux version 6.8.0-generic\n")
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")
            _write(root, "etc/os-release", 'PRETTY_NAME="Ubuntu 24.04 LTS"\n')

            report = _detector(root).detect()

        self.assertEqual(HostEnvironmentKind.NATIVE_LINUX, report.environment)
        self.assertEqual(report.distribution, "Ubuntu 24.04 LTS")
        self.assertEqual(report.kernel_release, "6.8.0-generic")
        self.assertFalse(report.windows_interop_available)

    def test_reads_wsl2_distribution_and_interop_environment_without_exposing_path(self):
        interop_value = "/run/WSL/123_interop"
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "proc/sys/kernel/osrelease",
                "6.1.21.2-microsoft-standard-WSL2\n",
            )

            report = _detector(
                root,
                {
                    "WSL_DISTRO_NAME": "Ubuntu-24.04",
                    "WSL_INTEROP": interop_value,
                },
            ).detect()

        self.assertEqual(HostEnvironmentKind.WSL2, report.environment)
        self.assertEqual(report.distribution, "Ubuntu-24.04")
        self.assertTrue(report.windows_interop_available)
        self.assertNotIn(interop_value, str(report.to_dict()))

    def test_reads_enabled_wsl_interop_marker(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "proc/sys/kernel/osrelease",
                "6.1.21.2-microsoft-standard-WSL2\n",
            )
            _write(root, "proc/sys/fs/binfmt_misc/WSLInterop", "enabled\n")

            report = _detector(root).detect()

        self.assertEqual(HostEnvironmentKind.WSL2, report.environment)
        self.assertTrue(report.windows_interop_available)

    def test_confirmed_wsl2_without_interop_reports_false(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "proc/sys/kernel/osrelease",
                "6.1.21.2-microsoft-standard-WSL2\n",
            )

            report = _detector(root, {"WSL_DISTRO_NAME": "Ubuntu"}).detect()

        self.assertEqual(HostEnvironmentKind.WSL2, report.environment)
        self.assertFalse(report.windows_interop_available)

    def test_unreadable_signal_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            detector = _detector(root)

            with patch.object(Path, "read_text", side_effect=OSError("denied")):
                report = detector.detect()

        self.assertEqual(HostEnvironmentKind.SANDBOX_UNVERIFIED, report.environment)

    def test_container_file_marker_takes_precedence_over_wsl(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "proc/sys/kernel/osrelease",
                "6.1.21.2-microsoft-standard-WSL2\n",
            )
            _write(root, ".dockerenv", "")

            report = _detector(root, {"WSL_DISTRO_NAME": "Ubuntu"}).detect()

        self.assertEqual(HostEnvironmentKind.SANDBOX_UNVERIFIED, report.environment)
        self.assertEqual(report.evidence["sandbox_signal"], "container_marker")

    def test_container_cgroup_marker_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")
            _write(root, "proc/self/cgroup", "0::/docker/synthetic\n")

            report = _detector(root).detect()

        self.assertEqual(HostEnvironmentKind.SANDBOX_UNVERIFIED, report.environment)

    def test_ci_marker_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")

            report = _detector(root, {"CI": "true"}).detect()

        self.assertEqual(HostEnvironmentKind.SANDBOX_UNVERIFIED, report.environment)
        self.assertEqual(report.evidence["sandbox_signal"], "ci_marker")

    def test_verified_live_runner_marker_allows_linux_ci_host(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")

            report = _detector(
                root,
                {"CI": "true", "GITHUB_ACTIONS": "true", "TSW_LIVE_RUNNER_VERIFIED": "1"},
            ).detect()

        self.assertEqual(HostEnvironmentKind.NATIVE_LINUX, report.environment)
        self.assertTrue(report.allows_live_setup)
        self.assertEqual(report.evidence["sandbox_signal"], "absent")

    def test_container_marker_cannot_be_overridden_by_verified_live_runner(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")
            _write(root, ".dockerenv", "")

            report = _detector(
                root,
                {"CI": "true", "TSW_LIVE_RUNNER_VERIFIED": "true"},
            ).detect()

        self.assertEqual(HostEnvironmentKind.SANDBOX_UNVERIFIED, report.environment)
        self.assertEqual(report.evidence["sandbox_signal"], "container_marker")

    def test_values_are_single_line_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\nignored\n")
            _write(root, "etc/os-release", 'PRETTY_NAME="Ubuntu   24.04"\n')

            report = _detector(root).detect()

        self.assertEqual(report.kernel_release, "6.8.0-generic")
        self.assertEqual(report.distribution, "Ubuntu 24.04")
        self.assertLessEqual(len(report.distribution), 160)

    def test_detection_executes_no_subprocess_and_writes_no_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")
            detector = _detector(root)

            with (
                patch.object(
                    subprocess,
                    "run",
                    side_effect=AssertionError("subprocess must not run"),
                ),
                patch.object(
                    os,
                    "system",
                    side_effect=AssertionError("shell must not run"),
                ),
                patch.object(
                    Path,
                    "write_text",
                    side_effect=AssertionError("files must not be written"),
                ),
            ):
                report = detector.detect()

        self.assertEqual(HostEnvironmentKind.NATIVE_LINUX, report.environment)


def _detector(
    root: Path,
    environment: dict[str, str] | None = None,
) -> HostEnvironmentDetector:
    return HostEnvironmentDetector(
        os_root=root,
        environment={} if environment is None else environment,
        platform_system=lambda: "Linux",
    )


def _write(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
