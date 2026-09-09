import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPOSITORY_ROOT / "install.sh"
INSTALLER_BOOTSTRAP_SOURCE_FILES = (
    Path("__init__.py"),
    Path("installer.py"),
    Path("simple_installer.py"),
    Path("domain/__init__.py"),
    Path("domain/configuration/__init__.py"),
    Path("domain/configuration/configuration_contract.py"),
    Path("domain/configuration/credential_resolution.py"),
    Path("domain/configuration/internal_test_credentials.py"),
    Path("domain/host_environment.py"),
    Path("domain/project_filesystem.py"),
    Path("domain/sanitized_evidence.py"),
    Path("application/__init__.py"),
    Path("application/services/__init__.py"),
    Path("application/services/credential_resolution.py"),
    Path("application/ports/__init__.py"),
    Path("application/ports/configuration/__init__.py"),
    Path("application/ports/configuration/port_configuration_source.py"),
    Path("application/ports/host/__init__.py"),
    Path("application/ports/host/port_host_environment_detector.py"),
    Path("application/ports/host/port_project_filesystem_inspector.py"),
    Path("application/ports/repositories/__init__.py"),
    Path("application/ports/repositories/port_project_filesystem_evidence_repository.py"),
    Path("infrastructure/__init__.py"),
    Path("infrastructure/adapters/__init__.py"),
    Path("infrastructure/adapters/configuration/__init__.py"),
    Path("infrastructure/adapters/configuration/configuration_sources.py"),
    Path("infrastructure/composition_operator_configuration.py"),
    Path("infrastructure/adapters/ingress/__init__.py"),
    Path("infrastructure/adapters/ingress/tls_state.py"),
    Path("infrastructure/adapters/preflight/__init__.py"),
    Path("infrastructure/adapters/preflight/windows_wsl_bridge_state.py"),
    Path("infrastructure/adapters/host/__init__.py"),
    Path("infrastructure/adapters/host/host_environment_detector.py"),
    Path("infrastructure/adapters/host/linux_host_signal_reader.py"),
    Path("infrastructure/adapters/host/project_filesystem_inspector.py"),
    Path("infrastructure/adapters/host/wsl_host_signal_reader.py"),
    Path("infrastructure/adapters/repositories/__init__.py"),
    Path("infrastructure/adapters/repositories/project_filesystem_evidence_local_repository.py"),
)


class TestInstallScript(unittest.TestCase):
    def test_installer_imports_without_third_party_site_packages(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-S",
                "-c",
                (
                    "import sys; import tiny_swarm_world.installer; "
                    "assert 'pydantic' not in sys.modules"
                ),
            ],
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONPATH": "src"},
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_install_runs_reset_before_setup_and_records_evidence(self):
        with _install_script_fixture() as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile service-access"
                    ),
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world setup run "
                        "--live --service-profile service-access"
                    ),
                ],
            )
            evidence_dir = fixture.single_evidence_dir()
            self.assertEqual((evidence_dir / "reset-run.exit").read_text().strip(), "0")
            self.assertEqual((evidence_dir / "setup-run.exit").read_text().strip(), "0")
            self.assertTrue((evidence_dir / "reset-run.log").is_file())
            self.assertTrue((evidence_dir / "setup-run.log").is_file())
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("fresh_install_reset=required", context)
            self.assertIn("host_runtime_type=native_linux", context)
            self.assertIn("host_runtime_detection_source=test_override", context)
            self.assertIn(
                ".tiny-swarm-world/evidence/installation-tests/native_linux/",
                context,
            )
            self.assertIn("live_execution_mode=interactive", context)
            self.assertIn("live_approval_source=operator_prompt", context)
            self.assertIn("terminal_recording_mode=terminal_recorder", context)
            self.assertIn("reset_confirmation_present=yes", context)
            self.assertIn("reset_confirmation_source=interactive_prompt", context)
            self.assertIn("reset_exit=0", context)
            self.assertIn("setup_exit=0", context)

    def test_install_aborts_setup_when_reset_fails(self):
        with _install_script_fixture(reset_exit=17) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 17)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile service-access"
                    ),
                ],
            )
            evidence_dir = fixture.single_evidence_dir()
            self.assertEqual((evidence_dir / "reset-run.exit").read_text().strip(), "17")
            self.assertFalse((evidence_dir / "setup-run.exit").exists())
            self.assertTrue((evidence_dir / "reset-run.log").is_file())
            self.assertFalse((evidence_dir / "setup-run.log").exists())
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("reset_exit=17", context)
            self.assertIn("setup_skipped_due_to_reset_failure=yes", context)
            self.assertIn("Setup will not start", result.stderr)

    def test_install_records_setup_failure_after_successful_reset(self):
        with _install_script_fixture(setup_exit=23) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 23)
            self.assertEqual(len(fixture.recorded_commands()), 2)
            evidence_dir = fixture.single_evidence_dir()
            self.assertEqual((evidence_dir / "reset-run.exit").read_text().strip(), "0")
            self.assertEqual((evidence_dir / "setup-run.exit").read_text().strip(), "23")
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("reset_exit=0", context)
            self.assertIn("setup_exit=23", context)
            self.assertNotIn("Installation completed successfully.", result.stdout)

    def test_install_forwards_selected_service_profile_to_reset_and_setup(self):
        with _install_script_fixture(extra_args=("--service-profile", "default")) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile default"
                    ),
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world setup run "
                        "--live --service-profile default"
                    ),
                ],
            )

    def test_install_forwards_explicit_wsl_filesystem_override_to_live_commands(self):
        with _install_script_fixture(
            extra_args=("--allow-wsl-windows-filesystem",),
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile service-access "
                        "--allow-wsl-windows-filesystem"
                    ),
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world setup run "
                        "--live --service-profile service-access "
                        "--allow-wsl-windows-filesystem"
                    ),
                ],
            )

    def test_install_refuses_missing_reset_confirmation_before_script_execution(self):
        with _install_script_fixture(reset_confirmation="wrong") as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 1)
            self.assertEqual(fixture.recorded_commands(), [])
            self.assertIn("confirmation did not match", result.stderr)

    def test_install_confirm_reset_flag_skips_interactive_reset_phrase(self):
        with _install_script_fixture(
            extra_args=("--confirm-reset",),
            reset_confirmation="",
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(fixture.recorded_commands()), 2)
            self.assertIn(
                "Fresh-install reset confirmed by explicit --confirm-reset flag.",
                result.stdout,
            )
            evidence_dir = fixture.single_evidence_dir()
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("reset_confirmation_present=yes", context)
            self.assertIn("reset_confirmation_source=explicit_flag", context)

    def test_install_uses_stateless_catalog_credentials(self):
        with _install_script_fixture(secret_environment={}) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(fixture.recorded_commands()), 2)
            self.assertIn("--live --confirm RESET_TINY_SWARM_PLATFORM --service-profile service-access", fixture.recorded_commands()[0])
            self.assertIn("setup run --live --service-profile service-access", fixture.recorded_commands()[1])
            evidence_dir = fixture.single_evidence_dir()
            context = (evidence_dir / "context.txt").read_text()
            self.assertNotIn("secrets_mode=", context)
            self.assertNotIn("secrets_generated_count=", context)
            self.assertIn("Credential convention: INTERNAL/TEST ONLY catalog defaults", result.stdout)
            self.assertNotIn("Password: TSW1234STW5678", result.stdout)
            self.assertIn("User:     admin@tiny-swarm-world.local", result.stdout)
            self.assertFalse(
                (fixture.root / ".tiny-swarm-world" / "local" / "live-installation.env").exists()
            )
            self.assertFalse(
                (fixture.root / ".tiny-swarm" / "secrets" / "generated.local.env").exists()
            )
    def test_interactive_install_does_not_pipe_live_consent_into_cli_prompt(self):
        with _install_script_fixture() as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fixture.recorded_live_confirmations(), ["", ""])

    def test_noninteractive_live_approval_flag_passes_explicit_cli_approval(self):
        with _install_script_fixture(
            extra_args=("--non-interactive-live-approval",),
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --approve-live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile service-access"
                    ),
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world setup run "
                        "--live --approve-live --service-profile service-access"
                    ),
                ],
            )
            evidence_dir = fixture.single_evidence_dir()
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("live_execution_mode=non_interactive", context)
            self.assertIn("live_approval_source=explicit_automation_flag", context)
            self.assertEqual(fixture.recorded_live_confirmations(), ["", ""])

    def test_headless_install_runs_governed_commands_without_terminal_recorder(self):
        with _install_script_fixture(
            extra_args=("--headless", "--non-interactive-live-approval"),
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world platform reset "
                        "--live --approve-live --confirm RESET_TINY_SWARM_PLATFORM "
                        "--service-profile service-access"
                    ),
                    (
                        "PYTHONPATH=src python3 -m tiny_swarm_world setup run "
                        "--live --approve-live --service-profile service-access"
                    ),
                ],
            )
            evidence_dir = fixture.single_evidence_dir()
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("terminal_recording_mode=headless", context)
            self.assertIn("live_execution_mode=non_interactive", context)
            self.assertEqual((evidence_dir / "reset-run.exit").read_text().strip(), "0")
            self.assertEqual((evidence_dir / "setup-run.exit").read_text().strip(), "0")
            self.assertIn("fake headless command", (evidence_dir / "reset-run.log").read_text())
            self.assertIn("fake headless command", (evidence_dir / "setup-run.log").read_text())
            self.assertFalse(fixture.recorded_live_confirmations())

    def test_headless_install_preserves_reset_failure_exit_code_and_skips_setup(self):
        with _install_script_fixture(
            reset_exit=17,
            extra_args=("--headless", "--non-interactive-live-approval"),
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 17)
            self.assertEqual(len(fixture.recorded_commands()), 1)
            evidence_dir = fixture.single_evidence_dir()
            self.assertEqual((evidence_dir / "reset-run.exit").read_text().strip(), "17")
            self.assertFalse((evidence_dir / "setup-run.exit").exists())
            self.assertFalse(fixture.recorded_live_confirmations())

    def test_headless_install_can_be_enabled_by_environment(self):
        with _install_script_fixture(
            extra_args=("--non-interactive-live-approval",),
            extra_environment={"TSW_INSTALL_HEADLESS": "1"},
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence_dir = fixture.single_evidence_dir()
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("terminal_recording_mode=headless", context)
            self.assertIn("fake headless command", (evidence_dir / "reset-run.log").read_text())
            self.assertIn("fake headless command", (evidence_dir / "setup-run.log").read_text())
            self.assertFalse(fixture.recorded_live_confirmations())

    def test_install_uses_private_configured_evidence_root(self):
        with _install_script_fixture() as fixture:
            evidence_root = fixture.root / "protected-evidence"
            fixture.extra_environment["TSW_LIVE_EVIDENCE_ROOT"] = evidence_root.as_posix()

            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence_dir = evidence_root / "native_linux" / next(
                child.name for child in (evidence_root / "native_linux").iterdir()
            )
            self.assertEqual(evidence_root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                (evidence_root / "native_linux").stat().st_mode & 0o777,
                0o700,
            )
            self.assertEqual(evidence_dir.stat().st_mode & 0o777, 0o700)
            self.assertIn(
                evidence_dir.as_posix(),
                (evidence_dir / "context.txt").read_text(),
            )

    def test_install_disables_infisical_item_seed_by_default(self):
        with _install_script_fixture() as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(fixture.recorded_seed_flags(), ["0", "0"])

    def test_native_linux_bootstraps_missing_python_dependencies_into_local_venv(self):
        with _install_script_fixture(
            skip_native_dependency_bootstrap=False,
            extra_environment={"TSW_INSTALL_TEST_FORCE_MISSING_IMPORTS": "1"},
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (fixture.root / ".tiny-swarm-world" / "install-venv" / "bin" / "python").is_file()
            )
            venv_python = (fixture.root / ".tiny-swarm-world" / "install-venv" / "bin" / "python").as_posix()
            self.assertEqual(
                fixture.recorded_commands(),
                [
                    (
                        f"PYTHONPATH=src {venv_python} -m tiny_swarm_world platform reset "
                        "--live --confirm RESET_TINY_SWARM_PLATFORM --service-profile service-access"
                    ),
                    (
                        f"PYTHONPATH=src {venv_python} -m tiny_swarm_world setup run "
                        "--live --service-profile service-access"
                    ),
                ],
            )

    def test_wsl_path_keeps_python3_when_dependency_bootstrap_is_skipped(self):
        with _install_script_fixture(
            extra_environment={
                "TSW_INSTALL_TEST_HOST_RUNTIME": "wsl2",
                "TSW_WINDOWS_EXPOSURE": "disabled",
                "WSL_DISTRO_NAME": "Ubuntu",
            },
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((fixture.root / ".tiny-swarm-world" / "install-venv").exists())
            self.assertIn("PYTHONPATH=src python3 -m tiny_swarm_world", fixture.recorded_commands()[0])
            evidence_dir = fixture.single_evidence_dir("wsl2")
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("host_runtime_type=wsl2", context)
            self.assertIn("host_runtime_detection_source=test_override", context)
            self.assertIn("windows_wsl_bridge_reason=windows_exposure_disabled", context)

    def test_native_linux_and_wsl2_use_distinct_evidence_directories(self):
        with _install_script_fixture() as native_fixture:
            native_result = native_fixture.run()

            self.assertEqual(native_result.returncode, 0, native_result.stderr)
            native_evidence_dir = native_fixture.single_evidence_dir("native_linux")
            self.assertIn(
                ".tiny-swarm-world/evidence/installation-tests/native_linux/",
                native_evidence_dir.as_posix(),
            )

        with _install_script_fixture(
            extra_environment={
                "TSW_INSTALL_TEST_HOST_RUNTIME": "wsl2",
                "TSW_WINDOWS_EXPOSURE": "disabled",
                "WSL_DISTRO_NAME": "Ubuntu",
            },
        ) as wsl_fixture:
            wsl_result = wsl_fixture.run()

            self.assertEqual(wsl_result.returncode, 0, wsl_result.stderr)
            wsl_evidence_dir = wsl_fixture.single_evidence_dir("wsl2")
            self.assertIn(
                ".tiny-swarm-world/evidence/installation-tests/wsl2/",
                wsl_evidence_dir.as_posix(),
            )

    def test_wsl_install_aborts_before_reset_when_windows_bridge_is_missing(self):
        with _install_script_fixture(
            extra_environment={
                "TSW_INSTALL_TEST_HOST_RUNTIME": "wsl2",
                "WSL_DISTRO_NAME": "Ubuntu",
            },
        ) as fixture:
            result = fixture.run()

            self.assertEqual(result.returncode, 1)
            self.assertEqual(fixture.recorded_commands(), [])
            evidence_dir = fixture.single_evidence_dir("wsl2")
            context = (evidence_dir / "context.txt").read_text()
            self.assertIn("windows_wsl_bridge_passed=no", context)
            self.assertIn("windows_wsl_bridge_reason=state_missing", context)
            self.assertIn("reset_skipped_due_to_windows_wsl_bridge=yes", context)
            self.assertFalse((evidence_dir / "reset-run.exit").exists())
            self.assertFalse((evidence_dir / "setup-run.exit").exists())
            self.assertIn("Windows <-> WSL bridge is not prepared", result.stderr)


class _InstallScriptFixture:
    def __init__(
        self,
        reset_exit: int = 0,
        setup_exit: int = 0,
        extra_args: tuple[str, ...] = (),
        reset_confirmation: str = "RESET_TINY_SWARM_PLATFORM",
        secret_environment: dict[str, str] | None = None,
        skip_native_dependency_bootstrap: bool = True,
        extra_environment: dict[str, str] | None = None,
    ):
        self.reset_exit = reset_exit
        self.setup_exit = setup_exit
        self.extra_args = extra_args
        self.reset_confirmation = reset_confirmation
        self.secret_environment = secret_environment
        self.skip_native_dependency_bootstrap = skip_native_dependency_bootstrap
        self.extra_environment = extra_environment or {}
        self._tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tempdir.name)
        self.fake_bin = self.root / "fake-bin"
        self.commands_file = self.root / "commands.txt"

    def __enter__(self):
        self._prepare()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._tempdir.cleanup()

    def run(self) -> subprocess.CompletedProcess[str]:
        env = {
            **{
                key: value
                for key, value in os.environ.items()
                if key
                not in (
                    *_install_secret_environment_names(),
                    *_wsl_environment_names(),
                )
            },
            **(
                _required_secret_environment()
                if self.secret_environment is None
                else self.secret_environment
            ),
            "PATH": f"{self.fake_bin}:{os.environ['PATH']}",
            "TSW_FAKE_SCRIPT_COMMANDS": str(self.commands_file),
            "TSW_FAKE_RESET_EXIT": str(self.reset_exit),
            "TSW_FAKE_SETUP_EXIT": str(self.setup_exit),
            "TSW_INSTALL_ENV_FILE": ".tiny-swarm-world/local/live-installation.env",
            "TSW_INSTALL_SKIP_NATIVE_DEPENDENCY_BOOTSTRAP": (
                "1" if self.skip_native_dependency_bootstrap else "0"
            ),
            "TSW_INSTALL_SKIP_NATIVE_GROUP_SWITCH": "1",
            "TSW_INSTALL_TEST_MODE": "1",
            "TSW_INSTALL_TEST_HOST_RUNTIME": "native_linux",
            "TSW_INSTALL_TEST_WINDOWS_WSL_BRIDGE_STATE_PATH": (
                ".tiny-swarm-world/test-windows-wsl-bridge-state.json"
            ),
            "TSW_LIVE_EVIDENCE_ROOT": ".tiny-swarm-world/evidence/installation-tests",
            "TSW_TEST_REAL_PYTHON": sys.executable,
            **self.extra_environment,
        }
        return subprocess.run(
            [
                "bash",
                str(self.root / "install.sh"),
                *self.extra_args,
            ],
            cwd=self.root,
            env=env,
            input=f"{self.reset_confirmation}\n",
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def recorded_commands(self) -> list[str]:
        if not self.commands_file.exists():
            return []
        return self.commands_file.read_text().splitlines()

    def recorded_live_confirmations(self) -> list[str]:
        confirmations_file = self.root / "live-confirmations.txt"
        if not confirmations_file.exists():
            return []
        return confirmations_file.read_text().splitlines()

    def recorded_seed_flags(self) -> list[str]:
        seed_file = self.root / "seed-flags.txt"
        if not seed_file.exists():
            return []
        return seed_file.read_text().splitlines()

    def single_evidence_dir(self, host_directory: str = "native_linux") -> Path:
        evidence_root = (
            self.root
            / ".tiny-swarm-world"
            / "evidence"
            / "installation-tests"
            / host_directory
        )
        evidence_dirs = tuple(evidence_root.iterdir())
        self_test = unittest.TestCase()
        self_test.assertEqual(1, len(evidence_dirs))
        return evidence_dirs[0]

    def _prepare(self) -> None:
        shutil.copy2(INSTALL_SCRIPT, self.root / "install.sh")
        package_source = REPOSITORY_ROOT / "src" / "tiny_swarm_world"
        package_target = self.root / "src" / "tiny_swarm_world"
        for relative_path in INSTALLER_BOOTSTRAP_SOURCE_FILES:
            target = package_target / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package_source / relative_path, target)
        (self.root / "infra" / "config" / "secrets").mkdir(parents=True)
        shutil.copy2(
            REPOSITORY_ROOT / "infra" / "config" / "secrets" / "infisical-secrets.yaml",
            self.root / "infra" / "config" / "secrets" / "infisical-secrets.yaml",
        )
        self.fake_bin.mkdir()
        tools_live_target = self.root / "tools" / "live"
        tools_live_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            REPOSITORY_ROOT / "tools" / "live" / "secure_runtime_paths.py",
            tools_live_target / "secure_runtime_paths.py",
        )
        _write_executable(self.fake_bin / "python3", _fake_python3())
        _write_executable(self.fake_bin / "grep", _fake_grep())
        _write_executable(self.fake_bin / "script", _fake_script())


def _install_script_fixture(
    reset_exit: int = 0,
    setup_exit: int = 0,
    extra_args: tuple[str, ...] = (),
    reset_confirmation: str = "RESET_TINY_SWARM_PLATFORM",
    secret_environment: dict[str, str] | None = None,
    skip_native_dependency_bootstrap: bool = True,
    extra_environment: dict[str, str] | None = None,
) -> _InstallScriptFixture:
    return _InstallScriptFixture(
        reset_exit=reset_exit,
        setup_exit=setup_exit,
        extra_args=extra_args,
        reset_confirmation=reset_confirmation,
        secret_environment=secret_environment,
        skip_native_dependency_bootstrap=skip_native_dependency_bootstrap,
        extra_environment=extra_environment,
    )


def _required_secret_environment() -> dict[str, str]:
    return {
        "TSW_PORTAINER_ADMIN_PASSWORD": "portainer-admin-password",
        "TSW_NEXUS_ADMIN_PASSWORD": "nexus-password",
        "TSW_JENKINS_ADMIN_PASSWORD": "jenkins-password",
        "TSW_SONARQUBE_ADMIN_PASSWORD": "sonarqube-password!",
        "TSW_POSTGRES_PASSWORD": "postgres-password",
        "TSW_SONARQUBE_POSTGRES_PASSWORD": "sonarqube-postgres-password",
        "TSW_PULSAR_TOKEN_SECRET_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        "TSW_PULSAR_ADMIN_TOKEN": "header.payload.signature",
        "TSW_PULSAR_MANAGER_ADMIN_PASSWORD": "pulsar-manager-password",
        "TSW_INFISICAL_LOGIN_EMAIL": "admin@tiny-swarm-world.local",
        "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD": "infisical-bootstrap-admin-password",
        "TSW_INFISICAL_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
        "TSW_INFISICAL_AUTH_SECRET": "infisical-auth-secret",
        "TSW_INFISICAL_POSTGRES_PASSWORD": "infisical-postgres-password",
        "TSW_INFISICAL_REDIS_PASSWORD": "infisical-redis-password",
        "TSW_TRAEFIK_GUI_USERS_HTPASSWD": "admin:$2y$12$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    }


def _install_secret_environment_names() -> tuple[str, ...]:
    return (
        *tuple(_required_secret_environment()),
        "TSW_TRAEFIK_TLS_CERT_SECRET_NAME",
        "TSW_TRAEFIK_TLS_KEY_SECRET_NAME",
        "TSW_TRAEFIK_GUI_USERS_SECRET_NAME",
    )


def _wsl_environment_names() -> tuple[str, ...]:
    return (
        "WSL_DISTRO_NAME",
        "WSL_INTEROP",
    )


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _fake_grep() -> str:
    return textwrap.dedent(
        """\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "$*" == *microsoft* || "$*" == *wsl* ]]; then
          exit 1
        fi
        exec /usr/bin/grep "$@"
        """
    )


def _fake_python3() -> str:
    return textwrap.dedent(
        """\
        #!/usr/bin/env bash
        set -euo pipefail
        if [[ "${1:-}" == "-c" ]]; then
          exit "${TSW_FAKE_IMPORT_CHECK_EXIT:-1}"
        fi
        if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then
          target="$3"
          mkdir -p "$target/bin"
          cat >"$target/bin/python" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" ]]; then
  exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then
  exit 0
fi
if [[ "${1:-}" == "-m" && "${2:-}" == "tiny_swarm_world" ]]; then
  printf 'PYTHONPATH=%s %s %s\\n' "${PYTHONPATH:-}" "$0" "$*" >>"$TSW_FAKE_SCRIPT_COMMANDS"
  printf 'fake headless command for %s\\n' "$*"
  case "$*" in
    *" platform reset "*)
      exit "$TSW_FAKE_RESET_EXIT"
      ;;
    *" setup run "*)
      exit "$TSW_FAKE_SETUP_EXIT"
      ;;
    *)
      exit 99
      ;;
  esac
fi
printf 'fake venv python should only handle import checks and pip\\n' >&2
exit 44
SH
          chmod 755 "$target/bin/python"
          exit 0
        fi
        if [[ "${1:-}" == "-m" && "${2:-}" == "tiny_swarm_world.installer" ]]; then
          exec "${TSW_TEST_REAL_PYTHON:-/usr/bin/python3}" "$@"
        fi
        if [[ "${1:-}" == "-m" && "${2:-}" == "tiny_swarm_world.simple_installer" ]]; then
          exec "${TSW_TEST_REAL_PYTHON:-/usr/bin/python3}" "$@"
        fi
        if [[ "${1:-}" == "-m" && "${2:-}" == "tiny_swarm_world" ]]; then
          printf 'PYTHONPATH=%s python3 %s\\n' "${PYTHONPATH:-}" "$*" >>"$TSW_FAKE_SCRIPT_COMMANDS"
          printf 'fake headless command for %s\\n' "$*"
          case "$*" in
            *" platform reset "*)
              exit "$TSW_FAKE_RESET_EXIT"
              ;;
            *" setup run "*)
              exit "$TSW_FAKE_SETUP_EXIT"
              ;;
            *)
              exit 99
              ;;
          esac
        fi
        printf 'fake python3 should be invoked only through fake script or secret generation\\n' >&2
        exit 43
        """
    )


def _fake_script() -> str:
    return textwrap.dedent(
        """\
        #!/usr/bin/env bash
        set -euo pipefail

        command_line=""
        log_file=""
        while [[ $# -gt 0 ]]; do
          case "$1" in
            -q|-e)
              shift
              ;;
            -c)
              command_line="$2"
              shift 2
              ;;
            *)
              log_file="$1"
              shift
              ;;
          esac
        done

        confirmation=""
        IFS= read -r confirmation || true
        printf '%s\\n' "$command_line" >>"$TSW_FAKE_SCRIPT_COMMANDS"
        printf '%s\\n' "$confirmation" >>"$(dirname "$TSW_FAKE_SCRIPT_COMMANDS")/live-confirmations.txt"
        printf '%s\\n' "${TSW_SEED_INFISICAL_ITEMS:-}" >>"$(dirname "$TSW_FAKE_SCRIPT_COMMANDS")/seed-flags.txt"
        mkdir -p "$(dirname "$log_file")"
        printf 'fake script log for %s\\n' "$command_line" >"$log_file"

        case "$command_line" in
          *" platform reset "*)
            exit "$TSW_FAKE_RESET_EXIT"
            ;;
          *" setup run "*)
            exit "$TSW_FAKE_SETUP_EXIT"
            ;;
          *)
            exit 99
            ;;
        esac
        """
    )



if __name__ == "__main__":
    unittest.main()
