import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from tiny_swarm_world import installer


class TestInstaller(unittest.TestCase):
    def test_installation_evidence_directory_uses_configured_xdg_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            state_root = Path(tempdir) / "state"

            evidence_dir = installer._installation_evidence_directory(
                {"XDG_STATE_HOME": state_root.as_posix()},
                cwd=Path(tempdir) / "checkout",
                host_runtime=installer.HostRuntime("wsl2", "test"),
                run_id="20260903T000000Z",
            )

            self.assertEqual(
                evidence_dir,
                state_root
                / "tiny-swarm-world"
                / "evidence"
                / "installation-tests"
                / "wsl2"
                / "20260903T000000Z",
            )
            self.assertEqual(evidence_dir.stat().st_mode & 0o777, 0o700)

    def test_installation_evidence_directory_uses_explicit_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            configured_root = Path(tempdir) / "configured"

            evidence_dir = installer._installation_evidence_directory(
                {"TSW_LIVE_EVIDENCE_ROOT": configured_root.as_posix()},
                cwd=Path(tempdir) / "checkout",
                host_runtime=installer.HostRuntime("native_linux", "test"),
                run_id="20260903T000002Z",
            )

            self.assertEqual(evidence_dir.parent, configured_root / "native_linux")

    def test_installation_evidence_directory_resolves_relative_root_from_checkout(self):
        with tempfile.TemporaryDirectory() as tempdir:
            checkout = Path(tempdir) / "checkout"
            evidence_dir = installer._installation_evidence_directory(
                {"TSW_LIVE_EVIDENCE_ROOT": "relative-evidence"},
                cwd=checkout,
                host_runtime=installer.HostRuntime("native_linux", "test"),
                run_id="20260903T000003Z",
            )

            self.assertEqual(evidence_dir.parent, checkout / "relative-evidence" / "native_linux")

    def test_installation_evidence_directory_uses_home_when_xdg_state_is_empty(self):
        with tempfile.TemporaryDirectory() as tempdir, patch.object(
            Path,
            "home",
            return_value=Path(tempdir),
        ):
            evidence_dir = installer._installation_evidence_directory(
                {"XDG_STATE_HOME": ""},
                cwd=Path(tempdir) / "checkout",
                host_runtime=installer.HostRuntime("native_linux", "test"),
                run_id="20260903T000001Z",
            )

            self.assertEqual(
                evidence_dir,
                Path(tempdir)
                / ".local"
                / "state"
                / "tiny-swarm-world"
                / "evidence"
                / "installation-tests"
                / "native_linux"
                / "20260903T000001Z",
            )
            self.assertEqual(evidence_dir.stat().st_mode & 0o777, 0o700)

    def test_fresh_install_requires_operator_provisioned_traefik_htpasswd(self):
        with tempfile.TemporaryDirectory() as tempdir:
            secret_env_file = Path(tempdir) / "live-installation.env"
            with self.assertRaisesRegex(
                installer.InstallerError,
                "TSW_TRAEFIK_GUI_USERS_HTPASSWD",
            ):
                installer._require_operator_provisioned_traefik_gui_users({}, secret_env_file)

            installer._require_operator_provisioned_traefik_gui_users(
                {"TSW_TRAEFIK_GUI_USERS_HTPASSWD": "admin:$2y$12$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
                secret_env_file,
            )

    def test_ensure_default_config_exports_adds_traefik_dashboard_secret_name(self):
        with tempfile.TemporaryDirectory():
            env: dict[str, str] = {}

            exports = installer._ensure_default_config_exports(env)

        self.assertEqual(
            exports["TSW_TRAEFIK_GUI_USERS_SECRET_NAME"],
            "tsw_traefik_gui_users",
        )
        self.assertEqual(
            env["TSW_TRAEFIK_GUI_USERS_SECRET_NAME"],
            "tsw_traefik_gui_users",
        )

    def test_ensure_default_config_exports_keeps_existing_secret_names(self):
        with tempfile.TemporaryDirectory():
            env = {
                "TSW_TRAEFIK_TLS_CERT_SECRET_NAME": "custom-cert",
                "TSW_TRAEFIK_TLS_KEY_SECRET_NAME": "custom-key",
                "TSW_TRAEFIK_GUI_USERS_SECRET_NAME": "custom-users",
                "TSW_LIVE_TLS_CA_BUNDLE": "/custom/ca-bundle.pem",
            }

            exports = installer._ensure_default_config_exports(env)

        self.assertEqual(exports, {})

    def test_default_trust_bundle_uses_external_ca_when_configured(self):
        with tempfile.TemporaryDirectory():
            env = {"TSW_TRAEFIK_CA_CERT_PATH": "/operator/ca.crt"}

            exports = installer._ensure_default_config_exports(env)

        self.assertEqual(exports["TSW_LIVE_TLS_CA_BUNDLE"], "/operator/ca.crt")

    def test_parse_args_defaults_to_service_access_and_internal_test_credentials(self):
        options = installer.parse_args(())

        self.assertEqual(options.service_profile, "service-access")
        self.assertFalse(options.confirm_reset)
        self.assertFalse(options.non_interactive_live_approval)
        self.assertFalse(options.headless)
        self.assertFalse(options.allow_wsl_windows_filesystem)

    def test_parse_args_supports_headless_and_noninteractive_approval(self):
        options = installer.parse_args(
            (
                "--service-profile",
                "default",
                "--confirm-reset",
                "--non-interactive-live-approval",
                "--allow-wsl-windows-filesystem",
                "--headless",
            )
        )

        self.assertEqual(options.service_profile, "default")
        self.assertTrue(options.confirm_reset)
        self.assertTrue(options.non_interactive_live_approval)
        self.assertTrue(options.allow_wsl_windows_filesystem)
        self.assertTrue(options.headless)

    def test_parse_args_rejects_removed_credential_options(self):
        for argv in (("--secrets-mode", "generated"), ("--no-generate-secrets",)):
            with self.subTest(argv=argv), patch.dict("os.environ", {"TSW_SECRETS_MODE": "generated"}):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    installer.parse_args(argv)

    def test_removed_credential_environment_selector_is_ignored(self):
        with patch.dict("os.environ", {"TSW_SECRETS_MODE": "generated"}):
            options = installer.parse_args(())

        self.assertFalse(hasattr(options, "secrets_mode"))
        self.assertFalse(hasattr(options, "generate_secrets"))

    def test_internal_test_installer_resolution_preserves_source_identity(self):
        entries = (
            installer.InstallerSecretEntry(
                key="TSW_PORTAINER_ADMIN_PASSWORD",
                source="internal_test_catalog",
                required=True,
            ),
        )
        resolved = installer._resolve_internal_test_installer_values(
            {
                "TSW_PORTAINER_ADMIN_PASSWORD": "operator-value",
                installer.CREDENTIAL_SOURCE_MAP_ENVIRONMENT: '{"TSW_PORTAINER_ADMIN_PASSWORD":"operator"}',
            },
            entries,
        )

        self.assertEqual("operator-value", resolved.values["TSW_PORTAINER_ADMIN_PASSWORD"])
        self.assertEqual("operator", resolved.sources["TSW_PORTAINER_ADMIN_PASSWORD"].value)

    def test_installer_source_context_is_redacted_to_source_labels(self):
        metadata = installer._safe_credential_source_metadata(
            {
                installer.CREDENTIAL_SOURCE_MAP_ENVIRONMENT: '{"TSW_PORTAINER_ADMIN_PASSWORD":"default"}',
            }
        )

        self.assertEqual('{"TSW_PORTAINER_ADMIN_PASSWORD":"default"}', metadata)
        self.assertEqual(
            "invalid",
            installer._safe_credential_source_metadata(
                {installer.CREDENTIAL_SOURCE_MAP_ENVIRONMENT: "not-json"}
            ),
        )

    def test_internal_test_run_routes_resolution_and_maps_resolution_errors(self):
        entries = (
            installer.InstallerSecretEntry(
                key="TSW_PORTAINER_ADMIN_PASSWORD",
                source="internal_test_catalog",
                required=True,
            ),
        )

        class StopAfterResolution(RuntimeError):
            pass

        for resolution_error in (False, True):
            with self.subTest(resolution_error=resolution_error), tempfile.TemporaryDirectory() as tempdir:
                patches = [
                    patch.object(installer, "_require_repository"),
                    patch.object(
                        installer,
                        "detect_host_runtime",
                        return_value=installer.HostRuntime("native_linux", "test"),
                    ),
                    patch.object(installer, "authorize_project_filesystem"),
                    patch.object(installer, "ensure_python_environment", return_value="python3"),
                    patch.object(
                        installer,
                        "_required_installer_secret_entries",
                        return_value=entries,
                    ),
                    patch.object(installer, "_normalize_infisical_login_email", return_value={}),
                    patch.object(installer, "_ensure_default_config_exports", return_value={}),
                    patch.object(installer, "_require_operator_provisioned_traefik_gui_users"),
                    patch.object(
                        installer,
                        "_probe_git_ignore",
                        return_value=installer._GitProbeResult(False, False, "outside_worktree"),
                    ),
                    patch.object(
                        installer,
                        "_collect_evidence_probe_snapshot",
                        return_value=installer._EvidenceProbeSnapshot(
                            "unknown", "unknown", "Linux", "test", "test"
                        ),
                    ),
                ]
                if resolution_error:
                    patches.append(
                        patch.object(
                            installer,
                            "_resolve_internal_test_installer_values",
                            side_effect=installer.CredentialResolutionError("invalid source metadata"),
                        )
                    )
                else:
                    patches.append(
                        patch.object(
                            installer,
                            "_write_context",
                            side_effect=StopAfterResolution,
                        )
                    )
                for active_patch in patches:
                    active_patch.start()
                try:
                    options = installer.parse_args(("--confirm-reset", "--headless"))
                    if resolution_error:
                        with self.assertRaisesRegex(installer.InstallerError, "invalid source metadata"):
                            installer.run(
                                options,
                                env={},
                                cwd=Path(tempdir),
                                reporter=Mock(),
                            )
                    else:
                        with self.assertRaises(StopAfterResolution):
                            installer.run(
                                options,
                                env={},
                                cwd=Path(tempdir),
                                reporter=Mock(),
                            )
                finally:
                    for active_patch in reversed(patches):
                        active_patch.stop()

    def test_detect_host_runtime_maps_typed_wsl2(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_host_signal(
                root,
                "proc/sys/kernel/osrelease",
                "6.1.0-microsoft-standard-WSL2\n",
            )

            runtime = installer.detect_host_runtime(
                {"WSL_DISTRO_NAME": "Ubuntu"},
                os_root=root,
                platform_system=lambda: "Linux",
            )

        self.assertEqual(runtime.name, "wsl2")
        self.assertEqual(runtime.detection_source, "wsl2")

    def test_detect_host_runtime_maps_typed_native_linux(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_host_signal(root, "proc/sys/kernel/osrelease", "6.8.0-generic\n")

            runtime = installer.detect_host_runtime(
                {},
                os_root=root,
                platform_system=lambda: "Linux",
            )

        self.assertEqual(runtime.name, "native_linux")
        self.assertEqual(runtime.detection_source, "native_linux")

    def test_detect_host_runtime_rejects_wsl1_and_ambiguous_signals(self):
        cases = (
            ("4.4.0-19041-Microsoft", {"WSL_DISTRO_NAME": "Ubuntu"}),
            ("6.8.0-generic", {"WSL_DISTRO_NAME": "Ubuntu"}),
            ("6.1.0-microsoft-standard-WSL2", {}),
        )
        for kernel_release, environment in cases:
            with self.subTest(kernel_release=kernel_release, environment=environment):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    _write_host_signal(
                        root,
                        "proc/sys/kernel/osrelease",
                        kernel_release,
                    )

                    with self.assertRaises(installer.InstallerError):
                        installer.detect_host_runtime(
                            environment,
                            os_root=root,
                            platform_system=lambda: "Linux",
                        )

    def test_host_runtime_test_override_requires_explicit_test_mode(self):
        with self.assertRaises(installer.InstallerError):
            installer.detect_host_runtime(
                {"TSW_INSTALL_TEST_HOST_RUNTIME": "wsl2"},
                os_root=Path("missing-test-root"),
                platform_system=lambda: "Linux",
            )

        runtime = installer.detect_host_runtime(
            {
                "TSW_INSTALL_TEST_MODE": "1",
                "TSW_INSTALL_TEST_HOST_RUNTIME": "wsl2",
            },
            os_root=Path("missing-test-root"),
            platform_system=lambda: "Linux",
        )

        self.assertEqual(runtime.name, "wsl2")
        self.assertEqual(runtime.detection_source, "test_override")

    def test_installer_stops_unsupported_host_before_bootstrap_or_file_writes(self):
        with (
            patch.object(
                installer,
                "detect_host_runtime",
                side_effect=installer.InstallerError("unsupported host"),
            ),
            patch.object(installer, "ensure_python_environment") as ensure_python,
        ):
            with self.assertRaises(installer.InstallerError):
                installer.run(
                    installer.parse_args(("--confirm-reset",)),
                    env={},
                    cwd=Path.cwd(),
                )

        ensure_python.assert_not_called()

    def test_installer_stops_blocked_wsl_filesystem_before_bootstrap_or_file_writes(self):
        runtime = installer.HostRuntime("wsl2", "test")
        with (
            patch.object(installer, "detect_host_runtime", return_value=runtime),
            patch.object(
                installer,
                "authorize_project_filesystem",
                side_effect=installer.InstallerError(
                    "Windows-mounted WSL project filesystem is blocked."
                ),
            ) as authorize,
            patch.object(installer, "ensure_python_environment") as ensure_python,
            patch.object(installer.subprocess, "run") as run_process,
        ):
            with self.assertRaises(installer.InstallerError):
                installer.run(
                    installer.parse_args(("--confirm-reset",)),
                    env={},
                    cwd=Path.cwd(),
                )

        authorize.assert_called_once_with(
            runtime,
            Path.cwd(),
            allow_wsl_windows_filesystem=False,
            env={},
        )
        ensure_python.assert_not_called()
        run_process.assert_not_called()

    def test_installer_orders_host_filesystem_before_dependency_bootstrap(self):
        calls: list[str] = []
        runtime = installer.HostRuntime("native_linux", "test")

        def detect(_: object) -> installer.HostRuntime:
            calls.append("host")
            return runtime

        def authorize(*args: object, **kwargs: object) -> object:
            calls.append("filesystem")
            raise installer.InstallerError("stop after filesystem checkpoint")

        with (
            patch.object(installer, "detect_host_runtime", side_effect=detect),
            patch.object(installer, "authorize_project_filesystem", side_effect=authorize),
            patch.object(
                installer,
                "ensure_python_environment",
                side_effect=lambda *args, **kwargs: calls.append("bootstrap"),
            ),
        ):
            with self.assertRaises(installer.InstallerError):
                installer.run(
                    installer.parse_args(("--confirm-reset",)),
                    env={},
                    cwd=Path.cwd(),
                )

        self.assertEqual(calls, ["host", "filesystem"])

    def test_ensure_python_environment_keeps_wsl_python_when_imports_available(self):
        with tempfile.TemporaryDirectory() as tempdir:
            paths = installer.InstallerPaths(
                secret_env_file=Path(tempdir) / "local.env",
                native_linux_venv=Path(tempdir) / "install-venv",
            )

            with patch.object(installer, "_python_imports_available", return_value=True):
                python_bin = installer.ensure_python_environment(
                    installer.HostRuntime("wsl2", "test"),
                    paths,
                    {},
                )

        self.assertEqual(python_bin, "python3")

    def test_ensure_python_environment_bootstraps_wsl_when_imports_are_missing(self):
        with tempfile.TemporaryDirectory() as tempdir:
            paths = installer.InstallerPaths(
                secret_env_file=Path(tempdir) / "local.env",
                native_linux_venv=Path(tempdir) / "install-venv",
            )
            venv_python = paths.native_linux_venv / "bin" / "python"
            commands: list[list[str]] = []

            def fake_imports_available(python_bin: str, env: object) -> bool:
                return python_bin == venv_python.as_posix()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                commands.append(command)
                if command[:3] == ["python3", "-m", "venv"]:
                    venv_python.parent.mkdir(parents=True)
                    venv_python.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0)
                if command[:3] == [venv_python.as_posix(), "-m", "pip"]:
                    return subprocess.CompletedProcess(command, 0)
                return subprocess.CompletedProcess(command, 99)

            with (
                patch.object(installer, "_python_imports_available", side_effect=fake_imports_available),
                patch.object(installer.subprocess, "run", side_effect=fake_run),
            ):
                python_bin = installer.ensure_python_environment(
                    installer.HostRuntime("wsl2", "test"),
                    paths,
                    {},
                )

        self.assertEqual(venv_python.as_posix(), python_bin)
        self.assertEqual(
            commands,
            [
                ["python3", "-m", "venv", paths.native_linux_venv.as_posix()],
                [venv_python.as_posix(), "-m", "pip", "install", "--upgrade", "pip"],
                [
                    venv_python.as_posix(),
                    "-m",
                    "pip",
                    "install",
                    "--require-hashes",
                    "-r",
                    "requirements.lock",
                ],
                [
                    venv_python.as_posix(),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "-e",
                    ".",
                ],
            ],
        )

    def test_installer_subprocess_timeout_is_configurable_and_positive(self):
        self.assertEqual(
            12.5,
            installer._installer_subprocess_timeout_seconds(
                {installer.INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT: "12.5"}
            ),
        )
        with self.assertRaises(installer.InstallerError):
            installer._installer_subprocess_timeout_seconds(
                {installer.INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT: "0"}
            )

    def test_installer_subprocess_timeout_is_reported_as_installer_error(self):
        with patch.object(
            installer.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["python3", "-m", "pip"], 1),
        ):
            with self.assertRaisesRegex(installer.InstallerError, "timed out"):
                installer._run_installer_subprocess(
                    ["python3", "-m", "pip"],
                    env={},
                    check=False,
                    timeout_seconds=1,
                )

    def test_normalized_email_value_removes_accidental_literal_quote(self):
        self.assertEqual(
            installer._normalized_email_value("'admin@tiny-swarm-world.local"),
            "admin@tiny-swarm-world.local",
        )

    def test_git_ignore_probe_batches_worktree_and_ignore_decision(self):
        completed = subprocess.CompletedProcess(
            ["git", "check-ignore"],
            returncode=0,
        )
        with patch.object(installer.subprocess, "run", return_value=completed) as run:
            result = installer._probe_git_ignore(Path("/tmp/repository"), ".tiny-swarm-world/")

        run.assert_called_once()
        self.assertEqual(
            result,
            installer._GitProbeResult(True, True, "ignored"),
        )

    def test_git_ignore_probe_classifies_optional_failures(self):
        for returncode, expected in (
            (1, (True, False, "not_ignored")),
            (128, (False, False, "outside_worktree")),
        ):
            with self.subTest(returncode=returncode):
                completed = subprocess.CompletedProcess(
                    ["git", "check-ignore"],
                    returncode=returncode,
                )
                with patch.object(installer.subprocess, "run", return_value=completed):
                    result = installer._probe_git_ignore(
                        Path("/tmp/repository"),
                        ".tiny-swarm-world/",
                    )

                self.assertEqual(
                    (result.inside_worktree, result.path_ignored, result.status),
                    expected,
                )

    def test_native_group_boundary_does_not_probe_or_mutate_host_state(self):
        env = {"TSW_INSTALL_COMMAND_GROUP": "lxd"}
        with patch.object(installer.subprocess, "run") as run:
            installer._configure_native_linux_command_group(
                installer.HostRuntime("native_linux", "test"),
                env,
            )

        run.assert_not_called()
        self.assertEqual(env, {"TSW_INSTALL_COMMAND_GROUP": "lxd"})

    def test_evidence_probe_snapshot_coalesces_git_and_system_metadata(self):
        calls = []

        def optional_text(command, *, cwd=None):
            calls.append((command, cwd))
            if command[0] == "git":
                return "HEAD -> main, origin/main\x001234567"
            return "Linux 6.18.33-test x86_64"

        git_probe = installer._GitProbeResult(True, True, "ignored")
        with patch.object(installer, "_run_optional_text", side_effect=optional_text):
            with patch.object(installer, "_read_text", return_value="6.18.33-test\n"):
                snapshot = installer._collect_evidence_probe_snapshot(
                    Path("/tmp/repository"),
                    git_probe,
                )

        self.assertEqual(snapshot.git_branch, "main")
        self.assertEqual(snapshot.git_head, "1234567")
        self.assertEqual(snapshot.platform_system, "Linux")
        self.assertEqual(snapshot.kernel_release, "6.18.33-test")
        self.assertEqual(snapshot.proc_osrelease, "6.18.33-test")
        self.assertEqual([command for command, _ in calls], [
            ("git", "show", "-s", "--format=%D%x00%h", "HEAD"),
            ("uname", "-srm"),
        ])

    def test_evidence_probe_snapshot_uses_unknown_for_optional_failures(self):
        git_probe = installer._GitProbeResult(True, True, "ignored")
        with patch.object(installer, "_run_optional_text", return_value="unknown"):
            with patch.object(installer, "_read_text", return_value=""):
                snapshot = installer._collect_evidence_probe_snapshot(
                    Path("/tmp/repository"),
                    git_probe,
                )

        self.assertEqual(
            snapshot,
            installer._EvidenceProbeSnapshot("unknown", "unknown", "unknown", "unknown", "unknown"),
        )

    def test_required_installer_secret_entries_come_from_manifest(self):
        entries = installer._required_installer_secret_entries(
            Path("infra/config/secrets/infisical-secrets.yaml")
        )
        keys = {entry.key for entry in entries}

        self.assertIn("TSW_PORTAINER_ADMIN_PASSWORD", keys)
        self.assertIn("TSW_INFISICAL_REDIS_PASSWORD", keys)
        self.assertNotIn("TSW_TRAEFIK_TLS_CERT_SECRET_NAME", keys)

    def test_required_installer_secret_entries_reject_type_source_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "infisical-secrets.yaml"
            manifest.write_text(
                "secrets:\n"
                "  - key: TSW_MISMATCHED_PASSWORD\n"
                "    type: external_user_secret\n"
                "    source: internal_test_catalog\n"
                "    required: true\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(installer.InstallerError, "type/source mismatch"):
                installer._required_installer_secret_entries(manifest)

    def test_confirm_reset_reports_missing_noninteractive_input(self):
        options = installer.InstallerOptions(
            service_profile="service-access",
            confirm_reset=False,
            non_interactive_live_approval=False,
            headless=False,
            allow_wsl_windows_filesystem=False,
        )

        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaisesRegex(installer.InstallerError, "was not provided"):
                installer._confirm_reset(options)

    def test_windows_wsl_bridge_guard_passes_for_native_linux_without_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            guard = _test_windows_wsl_bridge_guard(
                installer.HostRuntime("native_linux", "test"),
                {},
                Path(tempdir),
            )

        self.assertTrue(guard.passed)
        self.assertEqual(guard.reason, "not_wsl2")

    def test_windows_wsl_bridge_guard_blocks_wsl_without_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _write_ports_registry(root, (80, 10000))

            guard = _test_windows_wsl_bridge_guard(
                installer.HostRuntime("wsl2", "test"),
                {},
                root,
            )

        self.assertFalse(guard.passed)
        self.assertEqual(guard.reason, "state_missing")
        self.assertEqual(guard.missing_ports, (80, 10000))

    def test_windows_wsl_bridge_guard_accepts_current_state(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _write_ports_registry(root, (80, 10000))
            _write_windows_bridge_state(root, "172.20.0.2", (80, 10000))

            with patch(
                "tiny_swarm_world.infrastructure.adapters.preflight.windows_wsl_bridge_state.current_wsl_ipv4",
                return_value="172.20.0.2",
            ):
                guard = _test_windows_wsl_bridge_guard(
                    installer.HostRuntime("wsl2", "test"),
                    {},
                    root,
                )

        self.assertTrue(guard.passed)
        self.assertEqual(guard.reason, "prepared")

    def test_windows_wsl_bridge_guard_waits_for_reconcile_to_finish(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            _write_ports_registry(root, (80, 10000))
            _write_windows_bridge_state(root, "172.20.0.2", (80, 10000))
            state_path = root / "tools" / "windows" / ".tws-wsl-bridge.state.json"
            pending = json.loads(state_path.read_text(encoding="utf-8"))
            pending["agentStatus"] = "degraded"
            pending["driftReasons"] = ["reconcile_in_progress"]
            state_path.write_text(json.dumps(pending), encoding="utf-8")

            def finish_reconcile(_seconds: float) -> None:
                _write_windows_bridge_state(root, "172.20.0.2", (80, 10000))

            with (
                patch(
                    "tiny_swarm_world.infrastructure.adapters.preflight.windows_wsl_bridge_state.current_wsl_ipv4",
                    return_value="172.20.0.2",
                ),
                patch(
                    "tiny_swarm_world.infrastructure.adapters.preflight.windows_wsl_bridge_state.time.sleep",
                    side_effect=finish_reconcile,
                ) as sleep,
            ):
                guard = _test_windows_wsl_bridge_guard(
                    installer.HostRuntime("wsl2", "test"),
                    {},
                    root,
                )

        self.assertTrue(guard.passed)
        self.assertEqual(guard.reason, "prepared")
        sleep.assert_called_once_with(0.5)

    def test_windows_wsl_bridge_guard_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tempdir:
            guard = _test_windows_wsl_bridge_guard(
                installer.HostRuntime("wsl2", "test"),
                {"TSW_WINDOWS_EXPOSURE": "disabled"},
                Path(tempdir),
            )

        self.assertTrue(guard.passed)
        self.assertEqual(guard.reason, "windows_exposure_disabled")

    def test_windows_wsl_bridge_agent_not_ready_suggests_service_restart(self):
        self.assertEqual(
            installer._windows_wsl_bridge_suggested_commands("agent_not_ready"),
            (
                'powershell.exe -NoProfile -Command "Restart-Service -Name TinySwarmWorldWslBridge"',
                "powershell.exe -ExecutionPolicy Bypass -File tools/windows/tws-wsl-bridge.ps1 -Action install",
            ),
        )

    def test_print_windows_wsl_bridge_failure_for_agent_not_ready_mentions_service(self):
        guard = installer.WindowsWslBridgeGuardResult(
            passed=False,
            reason="agent_not_ready",
            state_path=Path("tools/windows/.tws-wsl-bridge.state.json"),
        )
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            installer._print_windows_wsl_bridge_failure(guard, Path(".tiny-swarm-world/evidence/test"))

        rendered = stderr.getvalue()
        self.assertIn("Reason: agent_not_ready", rendered)
        self.assertIn("Or restart the existing Windows bridge service:", rendered)
        self.assertIn("Restart-Service -Name TinySwarmWorldWslBridge", rendered)

    def test_suggested_checks_for_phase_returns_phase_specific_commands(self):
        self.assertEqual(
            installer._suggested_checks_for_phase("setup platform"),
            (
                "incus exec swarm-manager -- docker node ls",
                "incus exec swarm-manager -- docker service ls",
            ),
        )
        self.assertEqual(
            installer._suggested_checks_for_phase(
                "setup platform",
                log_text="first_failure_reason: apt_repository_unreachable",
            ),
            (
                "./tsw doctor network",
                "./tsw network repair --linux-forwarding --apply",
                "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\windows\\doctor-portproxy.ps1",
            ),
        )
        self.assertEqual(
            installer._suggested_checks_for_phase("reset platform"),
            ("incus list", "docker context ls"),
        )
        self.assertEqual(installer._suggested_checks_for_phase("preflight"), ())

    def test_fallback_install_event_renderer_covers_status_branches(self):
        install_started = installer._FallbackInstallEvent(
            event_type="INSTALL_STARTED",
            status="STARTED",
            step="Install",
            message="starting",
        )
        step_started = installer._FallbackInstallEvent(
            event_type="STEP_STARTED",
            status="STARTED",
            step="Preflight",
            target="host",
            message="checking",
            sequence=1,
            total=2,
        )
        succeeded = installer._FallbackInstallEvent(
            event_type="STEP_SUCCEEDED",
            status="SUCCEEDED",
            step="Preflight",
            message="done",
        )
        unknown = installer._FallbackInstallEvent(
            event_type="STEP_SKIPPED",
            status="SKIPPED",
            step="Preflight",
            target="host",
        )

        self.assertEqual(
            installer._render_fallback_install_event(install_started),
            ("Tiny Swarm World Installer", "  RUNNING starting"),
        )
        self.assertEqual(
            installer._render_fallback_install_event(step_started),
            ("[1/2] Preflight", "  RUNNING checking"),
        )
        self.assertEqual(installer._render_fallback_install_event(succeeded), ("  OK      done",))
        self.assertEqual(installer._render_fallback_install_event(unknown), ("  SKIPPED host",))

    def test_default_install_completion_summary_is_line_based(self):
        output = io.StringIO()

        with redirect_stdout(output):
            installer._print_install_completion_summary(
                0,
                Path(".tiny-swarm-world/evidence/install"),
                stream=output,
            )

        rendered = output.getvalue()
        self.assertEqual(
            rendered.splitlines(),
            [
                "Installation completed successfully.",
                "Evidence directory: .tiny-swarm-world/evidence/install",
            ],
        )
        self.assertNotIn("{", rendered)
        self.assertNotIn("[", rendered)

    def test_confirm_reset_default_output_is_a_readable_line(self):
        options = installer.InstallerOptions(
            service_profile="service-access",
            confirm_reset=True,
            non_interactive_live_approval=False,
            headless=True,
            allow_wsl_windows_filesystem=False,
        )
        output = io.StringIO()

        with redirect_stdout(output):
            installer._confirm_reset(options)

        rendered = output.getvalue()
        self.assertEqual(
            rendered.strip(),
            "Fresh-install reset confirmed by explicit --confirm-reset flag.",
        )
        self.assertNotIn("{", rendered)
        self.assertNotIn("[", rendered)

    def test_log_tail_suppresses_structured_blocks_but_keeps_evidence_reference(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "setup-run.log"
            log_path.write_text(
                "\n".join(
                    (
                        "human-readable failure detail",
                        "{",
                        '  \"secret\": \"retain only in evidence\",',
                        '  \"status\": \"failed\"',
                        "}",
                    )
                ),
                encoding="utf-8",
            )
            output = io.StringIO()

            with redirect_stderr(output):
                installer._print_tail(log_path, "Last log lines")

        rendered = output.getvalue()
        self.assertIn("human-readable failure detail", rendered)
        self.assertIn("structured log block omitted from console", rendered)
        self.assertIn(log_path.as_posix(), rendered)
        self.assertNotIn('"secret":', rendered)

    def test_run_phase_emits_distinct_timeout_and_terminates_process(self):
        class Reporter:
            def __init__(self) -> None:
                self.events: list[object] = []

            def report(self, event: object) -> None:
                self.events.append(event)

        reporter = Reporter()
        options = installer.InstallerOptions(
            service_profile="service-access",
            confirm_reset=True,
            non_interactive_live_approval=True,
            headless=True,
            allow_wsl_windows_filesystem=True,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_file = Path(temporary_directory) / "phase.log"
            exit_code = installer._run_phase(
                "bounded phase",
                "sleep 1",
                log_file,
                options,
                {"TSW_INSTALL_PHASE_TIMEOUT_SECONDS": "0.05"},
                Path(temporary_directory),
                reporter,
            )

        self.assertEqual(124, exit_code)
        self.assertEqual("TIMED_OUT", getattr(reporter.events[-1], "status").value)

    def test_reset_failure_guidance_explains_privileged_lxc_block(self):
        log_text = "\n".join(
            (
                "classification: managed_nodes_reset_blocked",
                "first_failure_mismatch_reasons: unsafe_instance_config",
                "first_failure_unsafe_instance_settings: security.privileged",
            )
        )

        lines = installer._reset_failure_guidance_lines(log_text)

        rendered = "\n".join(lines)
        self.assertIn("security.privileged", rendered)
        self.assertIn("incus profile get docker-swarm security.privileged", rendered)
        self.assertIn("disposable Tiny Swarm World nodes", rendered)

    def test_reset_failure_guidance_stays_silent_for_other_reset_blocks(self):
        lines = installer._reset_failure_guidance_lines(
            "\n".join(
                (
                    "classification: managed_nodes_reset_blocked",
                    "first_failure_mismatch_reasons: unsafe_instance_devices",
                )
            )
        )

        self.assertEqual(lines, ())

    def test_setup_failure_guidance_explains_apt_repository_reachability(self):
        lines = installer._setup_failure_guidance_lines(
            "first_failure_reason: apt_repository_unreachable"
        )

        rendered = "\n".join(lines)
        self.assertIn("APT repositories", rendered)
        self.assertIn("./tsw doctor network", rendered)
        self.assertIn("./tsw network repair --linux-forwarding --apply", rendered)
        self.assertIn("does not change iptables", rendered)

    def test_setup_failure_guidance_stays_silent_for_other_setup_blocks(self):
        self.assertEqual(installer._setup_failure_guidance_lines("failed_to_apply"), ())


def _write_host_signal(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_ports_registry(root: Path, ports: tuple[int, ...]) -> None:
    registry = root / "infra" / "config" / "ports.yaml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "ports:",
    ]
    for index, port in enumerate(ports):
        lines.extend(
            (
                f"  - id: port-{index}",
                f"    service_id: service-{index}",
                f"    internal_port: {port}",
                f"    external_port: {port}",
                "    exposure: diagnostic",
                "    protocol: tcp",
            )
        )
    registry.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _test_windows_wsl_bridge_guard(
    host_runtime: installer.HostRuntime,
    env: dict[str, str],
    root: Path,
) -> installer.WindowsWslBridgeGuardResult:
    with patch.dict(
        env,
        {"TSW_WINDOWS_WSL_BRIDGE_STATE_PATH": "tools/windows/.tws-wsl-bridge.state.json"},
    ):
        return installer._windows_wsl_bridge_guard(host_runtime, env, root)


def _write_windows_bridge_state(root: Path, wsl_ip: str, ports: tuple[int, ...]) -> None:
    state_path = root / "tools" / "windows" / ".tws-wsl-bridge.state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "contractVersion": 2,
        "agentMode": "windows-service",
        "agentStatus": "ready",
        "serviceName": "TinySwarmWorldWslBridge",
        "bundleId": "B" * 64,
        "bundleHashes": {
            "ports.yaml": "A" * 64,
            "tws-wsl-bridge-service.ps1": "A" * 64,
            "tws-wsl-bridge.config.json": "A" * 64,
            "tws-wsl-bridge.ps1": "A" * 64,
        },
        "generatedAt": datetime.now(UTC).isoformat(),
        "wslIp": wsl_ip,
        "mappings": [
            {
                "name": f"port-{port}",
                "listenPort": port,
                "connectPort": port,
            }
            for port in ports
        ],
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
