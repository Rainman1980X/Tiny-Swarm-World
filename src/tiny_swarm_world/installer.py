from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import signal
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Protocol

from tiny_swarm_world.domain.host_environment import (
    HostEnvironmentKind,
    HostEnvironmentReport,
)
from tiny_swarm_world.domain.project_filesystem import (
    ProjectFilesystemAssessment,
    ProjectFilesystemDecision,
    assess_project_filesystem,
)
from tiny_swarm_world.application.ports.repositories.port_project_filesystem_evidence_repository import (
    ProjectFilesystemEvidenceError,
)
from tiny_swarm_world.infrastructure.adapters.host import (
    HostEnvironmentDetector,
    ProjectFilesystemInspector,
)
from tiny_swarm_world.infrastructure.adapters.repositories.project_filesystem_evidence_local_repository import (
    ProjectFilesystemEvidenceLocalRepository,
)
from tiny_swarm_world.infrastructure.adapters.ingress.tls_state import canonical_tls_state_root
from tiny_swarm_world.domain.configuration.configuration_contract import (
    validate_traefik_htpasswd,
)
from tiny_swarm_world.domain.configuration.credential_resolution import (
    CredentialResolutionError,
    CredentialSource,
)
from tiny_swarm_world.application.services.credential_resolution import (
    CREDENTIAL_SOURCE_MAP_ENVIRONMENT,
    CredentialResolutionService,
    CredentialResolutionSnapshot,
    decode_source_metadata,
)

RESET_CONFIRMATION = "RESET_TINY_SWARM_PLATFORM"
_RESET_RUN_LOG_FILE = "reset-run.log"
_SETUP_RUN_LOG_FILE = "setup-run.log"
DEFAULT_SERVICE_PROFILE = "service-access"
DEFAULT_SECRET_ENV_FILE = ".tiny-swarm-world/local/live-installation.env"
DEFAULT_NATIVE_LINUX_VENV = ".tiny-swarm-world/install-venv"
DEFAULT_SECRET_MANIFEST_PATH = Path("infra/config/secrets/infisical-secrets.yaml")
TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT = "TSW_TRAEFIK_GUI_USERS_HTPASSWD"
INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT = "TSW_INSTALL_SUBPROCESS_TIMEOUT_SECONDS"
DEFAULT_INSTALLER_SUBPROCESS_TIMEOUT_SECONDS = 900.0
DEFAULT_INSTALLER_PROBE_TIMEOUT_SECONDS = 10.0
WINDOWS_WSL_BRIDGE_MAX_AGE_SECONDS = 5 * 60
WINDOWS_EXPOSURE_ENVIRONMENT = "TSW_WINDOWS_EXPOSURE"
WINDOWS_WSL_BRIDGE_TEST_STATE_ENVIRONMENT = (
    "TSW_INSTALL_TEST_WINDOWS_WSL_BRIDGE_STATE_PATH"
)
_MANIFEST_TYPE_BY_SOURCE = {
    "internal_test_catalog": "managed_secret",
    "external_user_secret": "external_user_secret",
    "placeholder_only": "placeholder_only",
}


@dataclass(frozen=True)
class InstallerOptions:
    service_profile: str
    confirm_reset: bool
    non_interactive_live_approval: bool
    headless: bool
    allow_wsl_windows_filesystem: bool


@dataclass(frozen=True)
class InstallerPaths:
    secret_env_file: Path
    native_linux_venv: Path


@dataclass(frozen=True)
class _GitProbeResult:
    inside_worktree: bool
    path_ignored: bool
    status: str


@dataclass(frozen=True)
class _EvidenceProbeSnapshot:
    git_branch: str
    git_head: str
    platform_system: str
    kernel_release: str
    proc_osrelease: str


@dataclass(frozen=True)
class _InstallRunContext:
    run_id: str
    service_profile: str
    secret_env_file: Path
    checked_secret_keys: tuple[str, ...]
    host_runtime: HostRuntime
    live_execution_mode: str
    live_approval_source: str
    terminal_recording_mode: str
    cwd: Path
    env: Mapping[str, str]
    git_probe: _GitProbeResult
    evidence_probes: _EvidenceProbeSnapshot


@dataclass(frozen=True)
class HostRuntime:
    name: str
    detection_source: str
    environment_report: HostEnvironmentReport | None = None


@dataclass(frozen=True)
class InstallerSecretEntry:
    key: str
    source: str
    required: bool
    type: str = ""


@dataclass(frozen=True)
class WindowsWslBridgeGuardResult:
    passed: bool
    reason: str
    state_path: Path
    current_wsl_ip: str = ""
    state_wsl_ip: str = ""
    expected_ports: tuple[int, ...] = ()
    mapped_ports: tuple[int, ...] = ()
    missing_ports: tuple[int, ...] = ()


class InstallReporter(Protocol):
    def report(self, event: object) -> None:
        ...


@dataclass(frozen=True)
class _FallbackInstallEvent:
    event_type: str
    status: str
    step: str
    target: str = "host"
    message: str = ""
    reason: str | None = None
    evidence_path: Path | None = None
    suggested_commands: Sequence[str] = ()
    duration_seconds: float | None = None
    sequence: int | None = None
    total: int | None = None


class _FallbackInstallReporter:
    def report(self, event: object) -> None:
        if not isinstance(event, _FallbackInstallEvent):
            return
        stream = sys.stderr if event.status == "FAILED" else sys.stdout
        for line in _render_fallback_install_event(event):
            print(line, file=stream)


class InstallerError(RuntimeError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_args(argv), env=os.environ, cwd=Path.cwd())
    except InstallerError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def parse_args(argv: Sequence[str] | None = None) -> InstallerOptions:
    parser = argparse.ArgumentParser(description="Tiny Swarm World live installation wrapper.")
    parser.add_argument(
        "--service-profile",
        default=os.environ.get("SERVICE_PROFILE", DEFAULT_SERVICE_PROFILE),
        choices=("default", "service-access"),
        help="Service profile passed to setup run.",
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Confirm the governed fresh-install reset without prompting.",
    )
    parser.add_argument(
        "--non-interactive-live-approval",
        action="store_true",
        help="Pass explicit non-interactive live approval to the CLI.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Disable terminal recorder/TUI presentation and capture command output directly.",
    )
    parser.add_argument(
        "--allow-wsl-windows-filesystem",
        action="store_true",
        help=(
            "Allow a confirmed Windows-mounted WSL2 repository and record the "
            "applied override in protected local evidence."
        ),
    )
    args = parser.parse_args(argv)
    return InstallerOptions(
        service_profile=args.service_profile,
        confirm_reset=args.confirm_reset,
        non_interactive_live_approval=args.non_interactive_live_approval,
        headless=args.headless or os.environ.get("TSW_INSTALL_HEADLESS") == "1",
        allow_wsl_windows_filesystem=args.allow_wsl_windows_filesystem,
    )


def _phase_event(
    event_type: str,
    status: str,
    step: str,
    *,
    target: str = "host",
    message: str = "",
    reason: str | None = None,
    evidence_path: Path | None = None,
    suggested_commands: Sequence[str] = (),
    sequence: int | None = None,
    total: int | None = None,
) -> object:
    try:
        from tiny_swarm_world.domain.install import InstallEvent, InstallEventType, InstallStatus

        typed_event_type = InstallEventType(event_type)
        typed_status = InstallStatus(status)
        return InstallEvent(
            event_type=typed_event_type,
            status=typed_status,
            step=step,
            target=target,
            message=message,
            reason=reason,
            evidence_path=evidence_path,
            suggested_commands=tuple(suggested_commands),
            sequence=sequence,
            total=total,
        )
    except ModuleNotFoundError:
        return _FallbackInstallEvent(
        event_type=event_type,
        status=status,
        step=step,
        target=target,
        message=message,
        reason=reason,
        evidence_path=evidence_path,
        suggested_commands=tuple(suggested_commands),
        sequence=sequence,
        total=total,
    )


def _default_install_reporter() -> InstallReporter:
    try:
        from tiny_swarm_world.infrastructure.adapters.ui.install_reporter import default_install_reporter

        return default_install_reporter()
    except ModuleNotFoundError:
        return _FallbackInstallReporter()


def run(
    options: InstallerOptions,
    *,
    env: Mapping[str, str],
    cwd: Path,
    reporter: InstallReporter | None = None,
) -> int:
    install_reporter = reporter or _default_install_reporter()
    _require_repository(cwd)
    paths = _paths_from_env(env, cwd)
    host_runtime = detect_host_runtime(env)
    authorize_project_filesystem(
        host_runtime,
        cwd,
        allow_wsl_windows_filesystem=options.allow_wsl_windows_filesystem,
        env=env,
    )
    python_bin = ensure_python_environment(host_runtime, paths, env)
    install_env = dict(env)
    required_entries = _required_installer_secret_entries(cwd / DEFAULT_SECRET_MANIFEST_PATH)
    try:
        resolutions = _resolve_internal_test_installer_values(
            install_env,
            required_entries,
        )
    except CredentialResolutionError as error:
        raise InstallerError(str(error)) from error
    install_env.update(resolutions.values)
    install_env[CREDENTIAL_SOURCE_MAP_ENVIRONMENT] = resolutions.source_metadata()

    _normalize_infisical_login_email(install_env)
    _ensure_default_config_exports(install_env)
    _require_operator_provisioned_traefik_gui_users(install_env, paths.secret_env_file)
    install_env.setdefault("TSW_SEED_INFISICAL_ITEMS", "0")
    _configure_native_linux_command_group(host_runtime, install_env)

    git_probe = _probe_git_ignore(cwd, ".tiny-swarm-world/")
    if git_probe.inside_worktree and not git_probe.path_ignored:
        print(
            "WARN: .tiny-swarm-world/ is not ignored by git; do not commit local evidence or credential overrides.",
            file=sys.stderr,
        )

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = _installation_evidence_directory(
        env,
        cwd=cwd,
        host_runtime=host_runtime,
        run_id=run_id,
    )
    live_mode, approval_source, approval_argument = _live_approval(options)
    terminal_mode = "headless" if options.headless else "terminal_recorder"
    evidence_probes = _collect_evidence_probe_snapshot(cwd, git_probe)
    _write_context(
        evidence_dir,
        context=_InstallRunContext(
            run_id=run_id,
            service_profile=options.service_profile,
            secret_env_file=paths.secret_env_file,
            checked_secret_keys=tuple(entry.key for entry in required_entries),
            host_runtime=host_runtime,
            live_execution_mode=live_mode,
            live_approval_source=approval_source,
            terminal_recording_mode=terminal_mode,
            cwd=cwd,
            env=install_env,
            git_probe=git_probe,
            evidence_probes=evidence_probes,
        ),
    )

    _print_install_plan(
        cwd,
        options,
        evidence_dir,
    )
    install_reporter.report(
        _phase_event(
            "INSTALL_STARTED",
            "RUNNING",
            "install",
            message=(
                f"Mode: fresh-reset; Profile: {options.service_profile}; "
                f"Provider: {install_env.get('TSW_NODE_PROVIDER', 'lxc_native')}"
            ),
        )
    )
    _confirm_reset(options)
    if not options.headless and shutil.which("script") is None:
        raise InstallerError("Required command 'script' is not available for terminal recording. Use --headless to capture logs directly.")
    _append_context(
        evidence_dir,
        {
            "reset_confirmation_present": "yes",
            "reset_confirmation_source": "explicit_flag" if options.confirm_reset else "interactive_prompt",
        },
    )

    bridge_guard = _windows_wsl_bridge_guard(host_runtime, install_env, cwd)
    _append_context(
        evidence_dir,
        _windows_wsl_bridge_context(bridge_guard),
    )
    if not bridge_guard.passed:
        install_reporter.report(
            _phase_event(
                "INSTALL_FINISHED",
                "FAILED",
                "windows-wsl-bridge",
                reason="Windows <-> WSL bridge is not prepared.",
                evidence_path=evidence_dir,
                suggested_commands=_windows_wsl_bridge_suggested_commands(bridge_guard.reason),
            )
        )
        _print_windows_wsl_bridge_failure(bridge_guard, evidence_dir)
        _append_context(
            evidence_dir,
            {
                "reset_skipped_due_to_windows_wsl_bridge": "yes",
                "setup_skipped_due_to_windows_wsl_bridge": "yes",
                "finished_utc": _utc_timestamp(),
            },
        )
        return 1

    reset_command = _workflow_command(
        python_bin,
        "platform reset",
        f"--live{approval_argument} --confirm {RESET_CONFIRMATION} --service-profile {shlex.quote(options.service_profile)}"
        f"{_filesystem_override_argument(options)}",
    )
    setup_command = _workflow_command(
        python_bin,
        "setup run",
        f"--live{approval_argument} --service-profile {shlex.quote(options.service_profile)}"
        f"{_filesystem_override_argument(options)}",
    )

    reset_exit = _run_phase(
        "fresh-install reset",
        reset_command,
        evidence_dir / _RESET_RUN_LOG_FILE,
        options,
        install_env,
        cwd,
        install_reporter,
        sequence=1,
        total=2,
    )
    _write_text(evidence_dir / "reset-run.exit", f"{reset_exit}\n")
    _append_context(evidence_dir, {"reset_exit": str(reset_exit)})
    if reset_exit != 0:
        install_reporter.report(
            _phase_event(
                "INSTALL_FINISHED",
                "FAILED",
                "install",
                reason="Fresh-install reset failed. Setup was not started.",
                evidence_path=evidence_dir,
            )
        )
        print(f"Fresh-install reset failed with exit code {reset_exit}. Setup will not start.", file=sys.stderr)
        print(f"Evidence directory: {evidence_dir.as_posix()}", file=sys.stderr)
        _append_context(
            evidence_dir,
            {
                "setup_skipped_due_to_reset_failure": "yes",
                "finished_utc": _utc_timestamp(),
            },
        )
        _print_tail(evidence_dir / _RESET_RUN_LOG_FILE, "Last reset log lines")
        _print_reset_failure_guidance(evidence_dir / _RESET_RUN_LOG_FILE)
        return reset_exit

    setup_exit = _run_phase(
        "live setup",
        setup_command,
        evidence_dir / _SETUP_RUN_LOG_FILE,
        options,
        install_env,
        cwd,
        install_reporter,
        sequence=2,
        total=2,
    )
    _write_text(evidence_dir / "setup-run.exit", f"{setup_exit}\n")
    _append_context(
        evidence_dir,
        {
            "setup_exit": str(setup_exit),
            "finished_utc": _utc_timestamp(),
        },
    )
    if setup_exit == 0:
        install_reporter.report(
            _phase_event(
                "INSTALL_FINISHED",
                "SUCCEEDED",
                "install",
                message="Installation completed successfully.",
                evidence_path=evidence_dir,
            )
        )
        _print_install_completion_summary(0, evidence_dir, stream=sys.stdout)
    else:
        install_reporter.report(
            _phase_event(
                "INSTALL_FINISHED",
                "FAILED",
                "install",
                reason=f"Live setup failed with exit code {setup_exit}.",
                evidence_path=evidence_dir,
            )
        )
        _print_install_completion_summary(setup_exit, evidence_dir, stream=sys.stderr)
        _print_tail(evidence_dir / _SETUP_RUN_LOG_FILE, "Last log lines")
        _print_setup_failure_guidance(evidence_dir / _SETUP_RUN_LOG_FILE)
    return setup_exit


def _paths_from_env(env: Mapping[str, str], cwd: Path) -> InstallerPaths:
    def resolve(path_value: str) -> Path:
        path = Path(path_value)
        return path if path.is_absolute() else cwd / path

    return InstallerPaths(
        secret_env_file=resolve(env.get("TSW_INSTALL_ENV_FILE", DEFAULT_SECRET_ENV_FILE)),
        native_linux_venv=resolve(env.get("TSW_NATIVE_LINUX_VENV", DEFAULT_NATIVE_LINUX_VENV)),
    )


def _installation_evidence_directory(
    env: Mapping[str, str],
    *,
    cwd: Path,
    host_runtime: HostRuntime,
    run_id: str,
) -> Path:
    """Create installer evidence on the protected runtime filesystem."""
    configured_root = env.get("TSW_LIVE_EVIDENCE_ROOT", "").strip()
    if configured_root:
        root = Path(configured_root).expanduser()
    else:
        configured_state = env.get("XDG_STATE_HOME", "").strip()
        state_root = (
            Path(configured_state).expanduser()
            if configured_state
            else Path.home() / ".local" / "state"
        )
        root = state_root / "tiny-swarm-world" / "evidence" / "installation-tests"
    if not root.is_absolute():
        root = cwd / root

    # The source checkout may stay on /mnt/*, but mutable installer evidence
    # must live on the verified Linux-native filesystem. Setup preflight
    # validates the same configured root before platform mutation begins.
    from tools.live.secure_runtime_paths import ensure_secure_directory

    ensure_secure_directory(root)
    host_root = root / host_runtime.name
    ensure_secure_directory(host_root)
    evidence_dir = host_root / run_id
    evidence_dir.mkdir()
    evidence_dir.chmod(0o700)
    return evidence_dir


def _require_repository(cwd: Path) -> None:
    if not (cwd / "src" / "tiny_swarm_world").is_dir():
        raise InstallerError("Run this script from the Tiny Swarm World repository root.")


def _required_installer_secret_entries(
    manifest_path: Path,
) -> tuple[InstallerSecretEntry, ...]:
    try:
        import yaml

        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise InstallerError(f"Secret manifest is invalid: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("secrets"), list):
        raise InstallerError("Secret manifest is invalid: expected a secrets list.")
    entries = tuple(_installer_secret_entry(item) for item in payload["secrets"])
    return tuple(
        entry
        for entry in entries
        if entry.required and entry.source != "external_user_secret"
    )


def _installer_secret_entry(item: object) -> InstallerSecretEntry:
    if not isinstance(item, dict):
        raise InstallerError("Secret manifest is invalid: secret entries must be mappings.")
    key = str(item.get("key", ""))
    source = str(item.get("source", ""))
    entry_type = str(item.get("type", ""))
    if not key.startswith("TSW_"):
        raise InstallerError(f"Secret manifest is invalid: unsupported key {key!r}.")
    expected_type = _MANIFEST_TYPE_BY_SOURCE.get(source)
    if expected_type is not None and entry_type != expected_type:
        raise InstallerError(
            f"Secret manifest is invalid: type/source mismatch for {key}: "
            f"{entry_type}/{source}."
        )
    return InstallerSecretEntry(
        key=key,
        source=source,
        required=bool(item.get("required", False)),
        type=entry_type,
    )


def _resolve_internal_test_installer_values(
    install_env: Mapping[str, str],
    required_entries: Sequence[InstallerSecretEntry],
) -> CredentialResolutionSnapshot:
    resolution_keys = tuple(
        dict.fromkeys(
            (
                *(entry.key for entry in required_entries),
                TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT,
            )
        )
    )
    source_metadata = decode_source_metadata(
        install_env.get(CREDENTIAL_SOURCE_MAP_ENVIRONMENT)
    )
    operator_values = {
        key: (
            ""
            if source_metadata.get(key) is CredentialSource.DEFAULT
            else install_env.get(key, "")
        )
        for key in resolution_keys
    }
    return CredentialResolutionService().resolve_bootstrap(
        resolution_keys,
        operator_values=operator_values,
    )


def detect_host_runtime(
    env: Mapping[str, str],
    *,
    os_root: Path = Path("/"),
    platform_system: Callable[[], str] | None = None,
) -> HostRuntime:
    test_runtime = env.get("TSW_INSTALL_TEST_HOST_RUNTIME")
    if env.get("TSW_INSTALL_TEST_MODE") == "1" and test_runtime in {"wsl2", "native_linux"}:
        return HostRuntime(test_runtime, "test_override")
    report = HostEnvironmentDetector(
        os_root=os_root,
        environment=env,
        platform_system=platform_system,
    ).detect()
    if report.environment in {
        HostEnvironmentKind.NATIVE_LINUX,
        HostEnvironmentKind.WSL2,
    }:
        return HostRuntime(
            report.environment.value,
            str(report.evidence.get("classification", report.environment.value)),
            report,
        )
    remediation = " ".join(report.remediation) or "Use native Linux or WSL2."
    raise InstallerError(
        f"Unsupported host environment '{report.environment.value}'. {remediation}"
    )


def authorize_project_filesystem(
    host_runtime: HostRuntime,
    cwd: Path,
    *,
    allow_wsl_windows_filesystem: bool,
    env: Mapping[str, str],
) -> ProjectFilesystemAssessment:
    host_environment = (
        host_runtime.environment_report.environment
        if host_runtime.environment_report is not None
        else HostEnvironmentKind(host_runtime.name)
    )
    inspector = ProjectFilesystemInspector()
    inspection = inspector.inspect(cwd.as_posix(), host_environment)
    assessment = assess_project_filesystem(
        host_environment,
        inspection,
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
    )
    if assessment.decision is ProjectFilesystemDecision.ALLOWED_BY_OVERRIDE:
        repository = ProjectFilesystemEvidenceLocalRepository.from_environment(
            env,
            target_inspector=inspector,
        )
        recorded = assessment.mark_evidence_recorded()
        try:
            repository.write(recorded)
        except ProjectFilesystemEvidenceError as error:
            raise InstallerError(
                "The WSL filesystem override could not be recorded in protected "
                "Linux-native owner-only evidence."
            ) from error
        assessment = recorded
    if assessment.blocked:
        remediation = " ".join(assessment.remediation)
        raise InstallerError(
            "Project filesystem blocks live installation. "
            f"{remediation}"
        )
    return assessment


def _windows_wsl_bridge_guard(
    host_runtime: HostRuntime,
    env: Mapping[str, str],
    cwd: Path,
) -> WindowsWslBridgeGuardResult:
    from tiny_swarm_world.infrastructure.adapters.preflight.windows_wsl_bridge_state import (
        configured_windows_wsl_bridge_state_path,
    )

    configured_state_path = configured_windows_wsl_bridge_state_path(env)
    test_state_path = env.get(WINDOWS_WSL_BRIDGE_TEST_STATE_ENVIRONMENT, "").strip()
    if env.get("TSW_INSTALL_TEST_MODE") == "1" and test_state_path:
        configured_state_path = Path(test_state_path)
    state_path = (
        configured_state_path
        if configured_state_path.is_absolute()
        else cwd / configured_state_path
    )
    expected_ports = _windows_wsl_bridge_expected_ports(cwd)
    if host_runtime.name != "wsl2":
        return WindowsWslBridgeGuardResult(True, "not_wsl2", state_path, expected_ports=expected_ports)
    if not _windows_exposure_required(env):
        return WindowsWslBridgeGuardResult(
            True,
            "windows_exposure_disabled",
            state_path,
            expected_ports=expected_ports,
        )
    if not state_path.exists():
        return WindowsWslBridgeGuardResult(
            False,
            "state_missing",
            state_path,
            expected_ports=expected_ports,
            missing_ports=expected_ports,
        )
    from tiny_swarm_world.infrastructure.adapters.preflight.windows_wsl_bridge_state import (
        current_wsl_ipv4,
        windows_wsl_bridge_status,
    )

    status = windows_wsl_bridge_status(
        cwd,
        expected_ports,
        state_path=configured_state_path,
        max_age_seconds=WINDOWS_WSL_BRIDGE_MAX_AGE_SECONDS,
        current_wsl_ipv4=current_wsl_ipv4,
    )
    return WindowsWslBridgeGuardResult(
        status.prepared,
        status.reason,
        state_path,
        current_wsl_ip=status.current_wsl_ip,
        state_wsl_ip=status.state_wsl_ip,
        expected_ports=status.expected_ports,
        mapped_ports=status.mapped_ports,
        missing_ports=status.missing_ports,
    )


def _windows_exposure_required(env: Mapping[str, str]) -> bool:
    value = env.get(WINDOWS_EXPOSURE_ENVIRONMENT, "").strip().casefold()
    return value not in {"0", "false", "no", "off", "disabled"}


def _filesystem_override_argument(options: InstallerOptions) -> str:
    if options.allow_wsl_windows_filesystem:
        return " --allow-wsl-windows-filesystem"
    return ""


def _windows_wsl_bridge_expected_ports(cwd: Path) -> tuple[int, ...]:
    registry_path = cwd / "infra" / "config" / "ports.yaml"
    ports: set[int] = set()
    current: dict[str, str] | None = None
    in_ports = False
    ports_indent = 0

    def commit_current() -> None:
        if current is None or "external_port" not in current:
            return
        protocol = current.get("protocol", "tcp").casefold()
        if protocol != "tcp":
            return
        port_value = current["external_port"].strip()
        if not port_value.isdigit():
            return
        ports.add(int(port_value))

    for raw_line in _read_text(registry_path).splitlines():
        if not in_ports:
            if raw_line.strip() == "ports:":
                in_ports = True
                ports_indent = len(raw_line) - len(raw_line.lstrip(" "))
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if not raw_line:
            continue
        if indent <= ports_indent:
            break
        if raw_line.lstrip().startswith("- id:"):
            commit_current()
            current = {"id": _clean_yaml_scalar(raw_line.lstrip()[4:].strip())}
            continue
        if current is None:
            continue
        if raw_line.lstrip().startswith("external_port:"):
            _, _, value = raw_line.lstrip().partition(":")
            current["external_port"] = _clean_yaml_scalar(value)
            continue
        if raw_line.lstrip().startswith("protocol:"):
            _, _, value = raw_line.lstrip().partition(":")
            current["protocol"] = _clean_yaml_scalar(value)
            continue

    commit_current()
    return tuple(sorted(ports))


def _clean_yaml_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'")


def ensure_python_environment(
    host_runtime: HostRuntime,
    paths: InstallerPaths,
    env: Mapping[str, str],
) -> str:
    python_bin = "python3"
    if env.get("TSW_INSTALL_SKIP_NATIVE_DEPENDENCY_BOOTSTRAP") == "1":
        return python_bin
    if _python_imports_available(python_bin, env):
        return python_bin
    venv_python = paths.native_linux_venv / "bin" / "python"
    if venv_python.is_file() and _python_imports_available(venv_python.as_posix(), env):
        return venv_python.as_posix()
    runtime_label = "WSL" if host_runtime.name == "wsl2" else "Native Linux"
    print(
        f"{runtime_label} Python dependencies are missing; preparing {paths.native_linux_venv.as_posix()}.",
        file=sys.stderr,
    )
    if env.get("TSW_INSTALL_TEST_MODE") == "1" and env.get("TSW_INSTALL_TEST_FORCE_MISSING_IMPORTS") == "1":
        _write_test_venv_python(venv_python)
        if not _python_imports_available(venv_python.as_posix(), env):
            raise InstallerError("Native Linux Python dependency bootstrap did not make required modules importable.")
        return venv_python.as_posix()
    completed = _run_installer_subprocess(
        [python_bin, "-m", "venv", paths.native_linux_venv.as_posix()],
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise InstallerError(
            f"Could not create native Linux virtual environment at {paths.native_linux_venv.as_posix()}. "
            "Install python3-venv and rerun install.sh."
        )
    _run_installer_subprocess(
        [venv_python.as_posix(), "-m", "pip", "install", "--upgrade", "pip"],
        env=dict(env),
        check=True,
    )
    _run_installer_subprocess(
        [
            venv_python.as_posix(),
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "-r",
            "requirements.lock",
        ],
        env=dict(env),
        check=True,
    )
    _run_installer_subprocess(
        [venv_python.as_posix(), "-m", "pip", "install", "--no-deps", "-e", "."],
        env=dict(env),
        check=True,
    )
    if not _python_imports_available(venv_python.as_posix(), env):
        raise InstallerError("Native Linux Python dependency bootstrap did not make required modules importable.")
    return venv_python.as_posix()


def _write_test_venv_python(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'if [[ "${1:-}" == "-c" ]]; then exit 0; fi',
                'if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then exit 0; fi',
                "exit 44",
                "",
            )
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


def _python_imports_available(python_bin: str, env: Mapping[str, str]) -> bool:
    if (
        env.get("TSW_INSTALL_TEST_MODE") == "1"
        and env.get("TSW_INSTALL_TEST_FORCE_MISSING_IMPORTS") == "1"
        and python_bin == "python3"
    ):
        return False
    code = "import pydantic\nimport requests\nimport ruamel.yaml\nimport yaml\n"
    return _run_installer_subprocess(
        [python_bin, "-c", code],
        env=dict(env),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout_seconds=DEFAULT_INSTALLER_PROBE_TIMEOUT_SECONDS,
    ).returncode == 0


def _run_installer_subprocess(
    command: Sequence[str],
    *,
    env: Mapping[str, str],
    check: bool,
    timeout_seconds: float | None = None,
    stdout: int | IO[str] | None = None,
    stderr: int | IO[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else _installer_subprocess_timeout_seconds(env)
    )
    try:
        return subprocess.run(
            list(command),
            env=dict(env),
            check=check,
            timeout=timeout,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as exc:
        rendered = " ".join(str(part) for part in command[:3])
        raise InstallerError(
            f"Installer subprocess timed out after {timeout:g}s: {rendered}"
        ) from exc


def _installer_subprocess_timeout_seconds(env: Mapping[str, str]) -> float:
    raw = env.get(
        INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT,
        str(DEFAULT_INSTALLER_SUBPROCESS_TIMEOUT_SECONDS),
    ).strip()
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise InstallerError(
            f"{INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT} must be a positive number."
        ) from exc
    if timeout <= 0:
        raise InstallerError(
            f"{INSTALLER_SUBPROCESS_TIMEOUT_ENVIRONMENT} must be a positive number."
        )
    return timeout


def _ensure_default_config_exports(
    env: dict[str, str],
) -> dict[str, str]:
    exports: dict[str, str] = {}
    if not env.get("TSW_TRAEFIK_TLS_CERT_SECRET_NAME"):
        exports["TSW_TRAEFIK_TLS_CERT_SECRET_NAME"] = "tsw_traefik_tls_cert"
    if not env.get("TSW_TRAEFIK_TLS_KEY_SECRET_NAME"):
        exports["TSW_TRAEFIK_TLS_KEY_SECRET_NAME"] = "tsw_traefik_tls_key"
    if not env.get("TSW_TRAEFIK_GUI_USERS_SECRET_NAME"):
        exports["TSW_TRAEFIK_GUI_USERS_SECRET_NAME"] = "tsw_traefik_gui_users"
    if not env.get("TSW_LIVE_TLS_CA_BUNDLE"):
        external_ca = env.get("TSW_TRAEFIK_CA_CERT_PATH", "").strip()
        exports["TSW_LIVE_TLS_CA_BUNDLE"] = external_ca or (
            canonical_tls_state_root(env) / "ca-bundle.pem"
        ).as_posix()
    if not exports:
        return {}
    env.update(exports)
    return exports


def _require_operator_provisioned_traefik_gui_users(
    env: Mapping[str, str],
    secret_env_file: Path,
) -> None:
    if env.get(TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT, "").strip():
        try:
            validate_traefik_htpasswd(env[TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT])
        except ValueError as exc:
            raise InstallerError("Traefik htpasswd material is invalid.") from exc
        return
    raise InstallerError(
        f"Required operator secret is missing: {TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT}. "
        f"Provide complete Traefik htpasswd content in {secret_env_file.as_posix()} "
        "before starting a fresh reset."
    )


def _normalize_infisical_login_email(env: dict[str, str]) -> dict[str, str]:
    current = env.get("TSW_INFISICAL_LOGIN_EMAIL", "")
    normalized = _normalized_email_value(current)
    if not normalized or normalized == current:
        return {}
    env["TSW_INFISICAL_LOGIN_EMAIL"] = normalized
    return {"TSW_INFISICAL_LOGIN_EMAIL": normalized}


def _normalized_email_value(value: str) -> str:
    stripped = value.strip()
    quote_stripped = stripped.strip("'\"")
    if quote_stripped and "@" in quote_stripped and "." in quote_stripped.partition("@")[2]:
        return quote_stripped
    return stripped


def _configure_native_linux_command_group(host_runtime: HostRuntime, env: dict[str, str]) -> None:
    """Keep native group switching caller-controlled and probe-free.

    The installer does not infer host identity or group membership. A caller
    that explicitly supplies ``TSW_INSTALL_COMMAND_GROUP`` may use it in the
    phase runner, while this bootstrap boundary performs no host mutation and
    does not persist membership state across invocations.
    """
    return


def _confirm_reset(options: InstallerOptions) -> None:
    if options.confirm_reset:
        print("Fresh-install reset confirmed by explicit --confirm-reset flag.")
        return
    print("Fresh install will reset configured Tiny Swarm World managed state.")
    try:
        answer = input(f"Type {RESET_CONFIRMATION} to continue: ")
    except EOFError:
        raise InstallerError("Fresh-install reset confirmation was not provided.") from None
    if answer != RESET_CONFIRMATION:
        raise InstallerError("Fresh-install reset confirmation did not match.")


def _live_approval(options: InstallerOptions) -> tuple[str, str, str]:
    if options.non_interactive_live_approval:
        return "non_interactive", "explicit_automation_flag", " --approve-live"
    return "interactive", "operator_prompt", ""


def _workflow_command(python_bin: str, workflow: str, args: str) -> str:
    return f"PYTHONPATH=src {shlex.quote(python_bin)} -m tiny_swarm_world {workflow} {args}"


def _run_phase(
    name: str,
    command: str,
    log_file: Path,
    options: InstallerOptions,
    env: Mapping[str, str],
    cwd: Path,
    reporter: InstallReporter | None = None,
    *,
    sequence: int | None = None,
    total: int | None = None,
) -> int:
    reporter = reporter or _default_install_reporter()
    reporter.report(
        _phase_event(
            "STEP_STARTED",
            "STARTED",
            name,
            message=f"{name} started",
            evidence_path=log_file,
            sequence=sequence,
            total=total,
        )
    )
    if options.headless:
        print(f"Starting {name}. Headless output is recorded at: {log_file.as_posix()}")
    else:
        print(f"Starting {name}. Terminal UI is visible and recorded at: {log_file.as_posix()}")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    effective_command = command
    if env.get("TSW_INSTALL_COMMAND_GROUP"):
        effective_command = f"sg {env['TSW_INSTALL_COMMAND_GROUP']} -c {shlex.quote(command)}"
    try:
        timeout_seconds = float(env.get("TSW_INSTALL_PHASE_TIMEOUT_SECONDS", "3600"))
    except ValueError as exc:
        raise InstallerError("TSW_INSTALL_PHASE_TIMEOUT_SECONDS must be a number.") from exc
    if timeout_seconds <= 0:
        raise InstallerError("TSW_INSTALL_PHASE_TIMEOUT_SECONDS must be positive.")
    timed_out = False
    interrupted = False
    if options.headless:
        with log_file.open("w", encoding="utf-8") as output:
            exit_code, timed_out, interrupted = _run_bounded_process(
                ["bash", "-lc", effective_command],
                cwd=cwd,
                env=env,
                timeout_seconds=timeout_seconds,
                stdout=output,
            )
    else:
        exit_code, timed_out, interrupted = _run_bounded_process(
            ["script", "-q", "-e", "-c", effective_command, log_file.as_posix()],
            cwd=cwd,
            env=env,
            timeout_seconds=timeout_seconds,
        )
    if timed_out or interrupted:
        status = "TIMED_OUT" if timed_out else "INTERRUPTED"
        event_type = "STEP_TIMED_OUT" if timed_out else "STEP_FAILED"
        reporter.report(
            _phase_event(
                event_type,
                status,
                name,
                reason=(
                    f"{name} exceeded its bounded timeout of {timeout_seconds:g} seconds."
                    if timed_out
                    else f"{name} was interrupted."
                ),
                evidence_path=log_file,
                suggested_commands=_suggested_checks_for_phase(
                    name,
                    log_text=_read_text(log_file),
                ),
                sequence=sequence,
                total=total,
            )
        )
        return 124 if timed_out else 130
    if exit_code == 0:
        reporter.report(
            _phase_event(
                "STEP_SUCCEEDED",
                "SUCCEEDED",
                name,
                message=f"{name} completed",
                evidence_path=log_file,
                sequence=sequence,
                total=total,
            )
        )
    else:
        reporter.report(
            _phase_event(
                "STEP_FAILED",
                "FAILED",
                name,
                reason=f"{name} exited with code {exit_code}.",
                evidence_path=log_file,
                suggested_commands=_suggested_checks_for_phase(
                    name,
                    log_text=_read_text(log_file),
                ),
                sequence=sequence,
                total=total,
            )
        )
    return exit_code


def _run_bounded_process(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    stdout: int | IO[str] | None = None,
) -> tuple[int, bool, bool]:
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(env),
        stdout=stdout,
        stderr=subprocess.STDOUT if stdout is not None else None,
        stdin=subprocess.DEVNULL,
        shell=False,
        start_new_session=True,
    )
    try:
        process.communicate(timeout=timeout_seconds)
        return process.returncode or 0, False, False
    except subprocess.TimeoutExpired:
        _terminate_process(process)
        return process.returncode if process.returncode is not None else 124, True, False
    except KeyboardInterrupt:
        _terminate_process(process)
        return process.returncode if process.returncode is not None else 130, False, True


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    process_group: int | None = None
    if os.name != "nt":
        try:
            process_group = os.getpgid(process.pid)
            os.killpg(process_group, signal.SIGTERM)
        except (OSError, AttributeError):
            process.terminate()
    else:
        process.terminate()
    try:
        process.communicate(timeout=3.0)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        if process_group is not None and os.name != "nt":
            os.killpg(process_group, signal.SIGKILL)
        else:
            process.kill()
    finally:
        process.communicate()


def _suggested_checks_for_phase(name: str, *, log_text: str = "") -> tuple[str, ...]:
    normalized = name.casefold()
    commands: list[str]
    if "setup" in normalized:
        if "apt_repository_unreachable" in log_text:
            commands = [
                "./tsw doctor network",
                "./tsw network repair --linux-forwarding --apply",
                "powershell.exe -ExecutionPolicy Bypass -File .\\tools\\windows\\doctor-portproxy.ps1",
            ]
        else:
            commands = [
                "incus exec swarm-manager -- docker node ls",
                "incus exec swarm-manager -- docker service ls",
            ]
    elif "reset" in normalized:
        commands = [
            "incus list",
            "docker context ls",
        ]
    else:
        commands = []
    return tuple(commands)


def _render_fallback_install_event(event: _FallbackInstallEvent) -> tuple[str, ...]:
    lines: list[str]
    if event.event_type == "INSTALL_STARTED":
        lines = [
            "Tiny Swarm World Installer",
            f"  RUNNING {_safe_installer_line_value(event.message or event.step)}",
        ]
        return tuple(lines)
    if event.status == "STARTED":
        header = (
            f"[{event.sequence}/{event.total}] {event.step}"
            if event.sequence and event.total
            else event.step
        )
        lines = [
            header,
            f"  RUNNING {_safe_installer_line_value(event.message or event.target)}",
        ]
        return tuple(lines)
    if event.status == "SUCCEEDED":
        lines = [
            f"  OK      {_safe_installer_line_value(event.message or event.target)}"
        ]
        return tuple(lines)
    if event.status in {"FAILED", "TIMED_OUT", "INTERRUPTED"}:
        target = f" on {event.target}" if event.target else ""
        lines = [f"FAILED {event.step}{target}"]
        if event.reason:
            lines.extend(("", "Reason:", f"  {_safe_installer_line_value(event.reason)}"))
        if event.evidence_path:
            lines.extend(("", "Evidence:", f"  {event.evidence_path.as_posix()}"))
        if event.suggested_commands:
            lines.extend(("", "Suggested checks:"))
            lines.extend(f"  {command}" for command in event.suggested_commands)
        return tuple(lines)
    lines = [
        f"  {event.status:<8}{_safe_installer_line_value(event.message or event.target)}"
    ]
    return tuple(lines)


def _safe_installer_line_value(value: str) -> str:
    text = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    if text.startswith(("{", "[")) and text.endswith(("}", "]")):
        return "structured event details recorded in evidence"
    return text


def _write_context(
    evidence_dir: Path,
    *,
    context: _InstallRunContext,
) -> None:
    values = {
        "run_id": context.run_id,
        "started_utc": _utc_timestamp(),
        "repo": context.cwd.as_posix(),
        "git_branch": context.evidence_probes.git_branch,
        "git_head": context.evidence_probes.git_head,
        "service_profile": context.service_profile,
        "fresh_install_reset": "required",
        "secret_env_file": context.secret_env_file.as_posix(),
        "checked_secret_keys": ",".join(context.checked_secret_keys),
        "credential_sources": _safe_credential_source_metadata(context.env),
        "host_runtime_type": context.host_runtime.name,
        "host_runtime_detection_source": context.host_runtime.detection_source,
        "selected_evidence_directory": evidence_dir.as_posix(),
        "live_execution_mode": context.live_execution_mode,
        "live_approval_source": context.live_approval_source,
        "terminal_recording_mode": context.terminal_recording_mode,
        "platform_system": context.evidence_probes.platform_system,
        "kernel_release": context.evidence_probes.kernel_release,
        "proc_osrelease": context.evidence_probes.proc_osrelease,
        "wsl_distro_name_present": "yes" if context.env.get("WSL_DISTRO_NAME") else "no",
        "wsl_interop_present": "yes" if context.env.get("WSL_INTEROP") else "no",
    }
    _append_context(evidence_dir, values, replace=True)


def _safe_credential_source_metadata(env: Mapping[str, str]) -> str:
    """Serialize only source labels for operator-readable run context."""
    try:
        sources = decode_source_metadata(env.get(CREDENTIAL_SOURCE_MAP_ENVIRONMENT))
    except CredentialResolutionError:
        return "invalid"
    return json.dumps(
        {key: source.value for key, source in sorted(sources.items())},
        separators=(",", ":"),
        sort_keys=True,
    )


def _append_context(evidence_dir: Path, values: Mapping[str, str], *, replace: bool = False) -> None:
    mode = "w" if replace else "a"
    with (evidence_dir / "context.txt").open(mode, encoding="utf-8") as context:
        for key, value in values.items():
            context.write(f"{key}={value}\n")


def _collect_evidence_probe_snapshot(
    cwd: Path,
    git_probe: _GitProbeResult,
) -> _EvidenceProbeSnapshot:
    git_branch, git_head = _git_revision_metadata(cwd, git_probe)
    system_metadata = _run_optional_text(("uname", "-srm"))
    if system_metadata == "unknown":
        platform_system = "unknown"
        kernel_release = "unknown"
    else:
        system_parts = system_metadata.split(maxsplit=2)
        platform_system = system_parts[0] if system_parts else "unknown"
        kernel_release = system_parts[1] if len(system_parts) > 1 else "unknown"
    proc_osrelease = _read_text(Path("/proc/sys/kernel/osrelease")).strip() or "unknown"
    return _EvidenceProbeSnapshot(
        git_branch=git_branch,
        git_head=git_head,
        platform_system=platform_system,
        kernel_release=kernel_release,
        proc_osrelease=proc_osrelease,
    )


def _git_revision_metadata(cwd: Path, git_probe: _GitProbeResult) -> tuple[str, str]:
    if not git_probe.inside_worktree:
        return "unknown", "unknown"
    metadata = _run_optional_text(
        ("git", "show", "-s", "--format=%D%x00%h", "HEAD"),
        cwd=cwd,
    )
    if metadata == "unknown":
        return "unknown", "unknown"
    decorations, separator, short_head = metadata.partition("\x00")
    if not separator:
        return "unknown", "unknown"
    branch = ""
    for decoration in decorations.split(","):
        candidate = decoration.strip()
        if candidate.startswith("HEAD -> "):
            branch = candidate.removeprefix("HEAD -> ")
            break
        if candidate.startswith("refs/heads/"):
            branch = candidate.removeprefix("refs/heads/")
    return branch, short_head or "unknown"


def _windows_wsl_bridge_context(
    guard: WindowsWslBridgeGuardResult,
) -> dict[str, str]:
    return {
        "windows_wsl_bridge_passed": "yes" if guard.passed else "no",
        "windows_wsl_bridge_reason": guard.reason,
        "windows_wsl_bridge_state_path": _relative_display_path(guard.state_path),
        "windows_wsl_bridge_current_wsl_ip": guard.current_wsl_ip,
        "windows_wsl_bridge_state_wsl_ip": guard.state_wsl_ip,
        "windows_wsl_bridge_expected_ports": _format_ints(guard.expected_ports),
        "windows_wsl_bridge_mapped_ports": _format_ints(guard.mapped_ports),
        "windows_wsl_bridge_missing_ports": _format_ints(guard.missing_ports),
    }


def _windows_wsl_bridge_suggested_commands(reason: str) -> tuple[str, ...]:
    if reason in {"wsl_ip_changed", "state_stale_by_age", "agent_not_ready"}:
        return (
            'powershell.exe -NoProfile -Command "Restart-Service -Name TinySwarmWorldWslBridge"',
            "powershell.exe -ExecutionPolicy Bypass -File tools/windows/tws-wsl-bridge.ps1 -Action install",
        )
    return (
        "powershell.exe -ExecutionPolicy Bypass -File tools/windows/tws-wsl-bridge.ps1 -Action install",
    )


def _print_windows_wsl_bridge_failure(
    guard: WindowsWslBridgeGuardResult,
    evidence_dir: Path,
) -> None:
    print("[FAIL] Windows <-> WSL bridge is not prepared.", file=sys.stderr)
    print(f"Reason: {guard.reason}", file=sys.stderr)
    print(f"State file: {_relative_display_path(guard.state_path)}", file=sys.stderr)
    if guard.current_wsl_ip or guard.state_wsl_ip:
        print(f"Current WSL IP: {guard.current_wsl_ip or 'unknown'}", file=sys.stderr)
        print(f"State WSL IP: {guard.state_wsl_ip or 'unknown'}", file=sys.stderr)
    if guard.missing_ports:
        print(f"Missing bridge ports: {_format_ints(guard.missing_ports)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Run PowerShell as Administrator:", file=sys.stderr)
    print("  tools/windows/tws-wsl-bridge.ps1 -Action install", file=sys.stderr)
    if guard.reason in {"wsl_ip_changed", "state_stale_by_age", "agent_not_ready"}:
        print("", file=sys.stderr)
        print("Or restart the existing Windows bridge service:", file=sys.stderr)
        print("  Restart-Service -Name TinySwarmWorldWslBridge", file=sys.stderr)
    print("", file=sys.stderr)
    print("To run WSL2 without Windows localhost exposure, set:", file=sys.stderr)
    print("  TSW_WINDOWS_EXPOSURE=disabled", file=sys.stderr)
    print(f"Evidence directory: {evidence_dir.as_posix()}", file=sys.stderr)


def _relative_display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _format_ints(values: Sequence[int]) -> str:
    return ",".join(str(value) for value in values)


def _print_install_plan(
    cwd: Path,
    options: InstallerOptions,
    evidence_dir: Path,
) -> None:
    print(
        "\n".join(
            (
                "Tiny Swarm World live installation",
                "",
                f"Repository:      {cwd.as_posix()}",
                f"Service profile: {options.service_profile}",
                f"Evidence:        {evidence_dir.as_posix()}",
                "Credentials:     deterministic catalog defaults plus explicit operator overrides",
                "",
                "This will run live infrastructure automation. It may create or change VMs,",
                "Docker resources, local service state, networks, and deployment artifacts.",
                "Fresh install starts by resetting configured Tiny Swarm World managed state.",
            )
        )
    )


def _print_install_completion_summary(
    exit_code: int,
    evidence_dir: Path,
    *,
    stream: IO[str],
) -> None:
    if exit_code == 0:
        print("Installation completed successfully.", file=stream)
    else:
        print(f"Installation failed with exit code {exit_code}.", file=stream)
    print(f"Evidence directory: {evidence_dir.as_posix()}", file=stream)


def _print_tail(path: Path, title: str) -> None:
    print(f"\n{title}:", file=sys.stderr)
    if not path.exists():
        return
    print(f"Full log retained at: {path.as_posix()}", file=sys.stderr)
    for line in _safe_log_tail_lines(path):
        print(line, file=sys.stderr)


def _safe_log_tail_lines(path: Path) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    rendered: list[str] = []
    structured_depth = 0
    for line in lines:
        stripped = line.strip()
        if structured_depth:
            structured_depth += _structured_delimiter_delta(stripped)
            if structured_depth <= 0:
                structured_depth = 0
            continue
        if _starts_structured_log_value(stripped):
            rendered.append(
                "[structured log block omitted from console; full content is in the evidence log]"
            )
            structured_depth = max(0, _structured_delimiter_delta(stripped))
            continue
        rendered.append(line)
    return tuple(rendered)


def _starts_structured_log_value(value: str) -> bool:
    if value.startswith("{"):
        return True
    return (
        value.startswith("[")
        and len(value) > 1
        and value[1] in "\"'{0123456789-]"
    )


def _structured_delimiter_delta(value: str) -> int:
    return value.count("{") + value.count("[") - value.count("}") - value.count("]")


def _print_reset_failure_guidance(path: Path) -> None:
    if not path.exists():
        return
    lines = _reset_failure_guidance_lines(
        path.read_text(encoding="utf-8", errors="replace")
    )
    if not lines:
        return
    print(file=sys.stderr)
    for line in lines:
        print(line, file=sys.stderr)


def _reset_failure_guidance_lines(log_text: str) -> tuple[str, ...]:
    if not _reset_log_mentions(
        log_text,
        "managed_nodes_reset_blocked",
        "unsafe_instance_config",
        "first_failure_unsafe_instance_settings: security.privileged",
    ):
        return ()
    return (
        "Reset recovery hint:",
        "  Existing configured LXC nodes are blocked by security.privileged.",
        "  Inspect instance and profile state from the same WSL/Linux shell:",
        "    for node in swarm-manager swarm-worker-1 swarm-worker-2; do",
        "      incus config get \"$node\" security.privileged",
        "    done",
        "    incus profile get docker-swarm security.privileged",
        "  If these are disposable Tiny Swarm World nodes, unset only the",
        "  setting that reports true, then rerun install.sh.",
        "  Details: documentation/user-handbook.adoc#_troubleshooting_checklist",
    )


def _reset_log_mentions(log_text: str, *needles: str) -> bool:
    return all(needle in log_text for needle in needles)


def _print_setup_failure_guidance(path: Path) -> None:
    if not path.exists():
        return
    lines = _setup_failure_guidance_lines(
        path.read_text(encoding="utf-8", errors="replace")
    )
    if not lines:
        return
    print(file=sys.stderr)
    for line in lines:
        print(line, file=sys.stderr)


def _setup_failure_guidance_lines(log_text: str) -> tuple[str, ...]:
    if "apt_repository_unreachable" not in log_text:
        return ()
    return (
        "Setup recovery hint:",
        "  Docker Engine installation inside the LXC nodes cannot reach APT repositories.",
        "  Run the read-only network diagnosis first:",
        "    ./tsw doctor network",
        "  If the diagnosis reports Docker blocking incusbr0 forwarding, apply only",
        "  the targeted forwarding repair:",
        "    ./tsw network repair --linux-forwarding --apply",
        "  If DNS or HTTP egress is blocked for another reason, fix that domain before",
        "  rerunning install.sh. The installer does not change iptables, Incus runtime",
        "  files, WSL mode, Windows portproxy, or Windows Firewall automatically.",
    )


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _run_text(command: tuple[str, ...], *, cwd: Path | None = None) -> str:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=DEFAULT_INSTALLER_PROBE_TIMEOUT_SECONDS,
    ).stdout.strip()


def _run_optional_text(command: tuple[str, ...], *, cwd: Path | None = None) -> str:
    try:
        result = _run_text(command, cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result or "unknown"


def _probe_git_ignore(cwd: Path, path: str) -> _GitProbeResult:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", path],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=DEFAULT_INSTALLER_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return _GitProbeResult(False, False, "unknown")
    if result.returncode == 0:
        return _GitProbeResult(True, True, "ignored")
    if result.returncode == 1:
        return _GitProbeResult(True, False, "not_ignored")
    if result.returncode == 128:
        return _GitProbeResult(False, False, "outside_worktree")
    return _GitProbeResult(False, False, f"unknown_{result.returncode}")


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
