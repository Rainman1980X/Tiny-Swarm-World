"""Diagnose Tiny Swarm World installation preconditions under Linux/WSL."""

from __future__ import annotations

import argparse
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
LIVE_TOOLS_ROOT = REPOSITORY_ROOT / "tools" / "live"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(LIVE_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(LIVE_TOOLS_ROOT))

from tools.live.secure_runtime_paths import (  # noqa: E402
    assess_evidence_directory,
    assess_secret_file,
    host_classification,
)

INSTALL_SCRIPT = "install.sh"
SECRET_ENV_FILE = ".tiny-swarm-world/local/live-installation.env"
EVIDENCE_ROOT = ".tiny-swarm-world/evidence/installation-tests"
SUPPORTED_EVIDENCE_HOST_DIRECTORIES = ("wsl2", "native_linux")
INSTALL_SH_EXECUTABLE_LABEL = "install.sh executable"
SECRET_FILE_MODE_LABEL = "Secret file mode"
EXCLUDED_SCAN_DIRS = {
    ".git",
    ".tiny-swarm-world",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "venv",
}
PERMISSION_SCAN_PATHS = (
    ".",
    "install.sh",
    "README.md",
    "requirements.txt",
    "tools",
    "src/tiny_swarm_world",
    "infra",
)
UNIT_SCAN_PATHS = (
    "infra",
    "tools",
    "documentation",
    "src/tiny_swarm_world",
)
UNIT_SUFFIXES = (".service", ".socket", ".timer")
STATUS_ORDER = {"OK": 0, "INFO": 1, "WARN": 2, "FAIL": 3, "FIXED": 1}


@dataclass(frozen=True)
class Finding:
    status: Literal["OK", "INFO", "WARN", "FAIL", "FIXED"]
    title: str
    detail: str
    remediation: tuple[str, ...] = ()


@dataclass(frozen=True)
class SystemdState:
    wsl: bool
    available: bool
    pid1: str
    wsl_conf_systemd: str
    systemctl_state: str = ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose Tiny Swarm World install.sh, WSL2/systemd and service logs.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPOSITORY_ROOT),
        help="Repository root to inspect. Defaults to the current Tiny Swarm World checkout.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Run live host diagnostics such as systemctl state checks. "
            "This does not start or stop services."
        ),
    )
    parser.add_argument(
        "--fix-permissions",
        action="store_true",
        help=(
            "With --live, repair narrow repository permissions: install.sh execute bit "
            "and local secret file mode 600. Ownership is reported, not changed."
        ),
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help=(
            "Explicit operator environment file. Relative paths are resolved from the "
            "repository root; live WSL runs require a WSL-native absolute path."
        ),
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    env_file = _resolve_env_file(repo_root, args.env_file)
    findings = diagnose(
        repo_root,
        live=args.live,
        fix_permissions=args.fix_permissions,
        env_file=env_file,
    )
    print_report(repo_root, findings, log_guidance(repo_root))
    return 1 if any(finding.status == "FAIL" for finding in findings) else 0


def diagnose(
    repo_root: Path,
    *,
    live: bool = False,
    fix_permissions: bool = False,
    env_file: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    if fix_permissions and not live:
        findings.append(
            Finding(
                "FAIL",
                "Permission repair requested without live mode",
                "--fix-permissions requires --live so mutating behavior is explicit.",
                ("Run: python3 tools/install_debugger.py --live --fix-permissions",),
            )
        )
        return findings

    findings.extend(check_repository_shape(repo_root))
    findings.extend(check_install_script(repo_root, live=live, fix_permissions=fix_permissions))
    configured_env_file = env_file or _resolve_env_file(repo_root, None)
    findings.extend(
        check_permissions(
            repo_root,
            live=live,
            fix_permissions=fix_permissions,
            env_file=configured_env_file,
        )
    )
    findings.extend(
        check_secure_runtime_paths(
            repo_root,
            live=live,
            env_file=configured_env_file,
        )
    )
    systemd_state, systemd_findings = check_systemd(live=live)
    findings.extend(systemd_findings)
    findings.extend(check_service_definitions(repo_root, systemd_state))
    findings.extend(check_latest_evidence(repo_root))
    return findings


def check_repository_shape(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not repo_root.exists():
        return [
            Finding(
                "FAIL",
                "Repository root missing",
                f"{repo_root} does not exist.",
            )
        ]
    if not (repo_root / "src" / "tiny_swarm_world").is_dir():
        findings.append(
            Finding(
                "FAIL",
                "Repository identity not found",
                "src/tiny_swarm_world is missing. Run the debugger from Tiny Swarm World.",
            )
        )
    else:
        findings.append(
            Finding(
                "OK",
                "Repository identity",
                "src/tiny_swarm_world is present.",
            )
        )
    if repo_root.as_posix().startswith("/mnt/"):
        findings.append(
            Finding(
                "INFO",
                "WSL mount path",
                f"Repository is on a WSL mounted path: {repo_root}",
                (
                    "Mounted Windows drives can expose permissive mode bits. "
                    "Treat chmod/chown findings as host-state diagnostics.",
                ),
            )
        )
    return findings


def check_install_script(
    repo_root: Path,
    *,
    live: bool,
    fix_permissions: bool,
) -> list[Finding]:
    path = repo_root / INSTALL_SCRIPT
    if not path.exists():
        return [Finding("FAIL", "install.sh missing", f"{path} was not found.")]

    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    findings.append(
        Finding(
            "OK" if text.startswith("#!/usr/bin/env bash") else "WARN",
            "install.sh shell",
            "Bash shebang is present." if text.startswith("#!/usr/bin/env bash") else (
                "install.sh does not start with #!/usr/bin/env bash."
            ),
        )
    )
    for needle, description in (
        ("tiny_swarm_world.simple_installer", "Python installer entry point"),
        ("PYTHONPATH", "source checkout Python path"),
    ):
        findings.append(
            Finding(
                "OK" if needle in text else "FAIL",
                f"install.sh {description}",
                f"Found {needle!r}." if needle in text else f"Missing {needle!r}.",
            )
        )

    executable = os.access(path, os.X_OK)
    if executable:
        findings.append(Finding("OK", INSTALL_SH_EXECUTABLE_LABEL, "install.sh is executable."))
    elif live and fix_permissions:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        findings.append(
            Finding("FIXED", INSTALL_SH_EXECUTABLE_LABEL, "Added owner execute bit to install.sh.")
        )
    else:
        findings.append(
            Finding(
                "FAIL",
                INSTALL_SH_EXECUTABLE_LABEL,
                "install.sh is not executable.",
                ("Run: chmod u+x install.sh",),
            )
        )
    return findings


def check_permissions(
    repo_root: Path,
    *,
    live: bool,
    fix_permissions: bool,
    env_file: Path | None = None,
) -> list[Finding]:
    findings = _filesystem_permission_findings(repo_root)
    secret_file = env_file or repo_root / SECRET_ENV_FILE
    findings.append(
        _secret_file_mode_finding(
            secret_file,
            live=live,
            fix_permissions=fix_permissions,
        )
    )
    return findings


def check_secure_runtime_paths(
    repo_root: Path,
    *,
    live: bool,
    env_file: Path,
) -> list[Finding]:
    """Check mutable secret/evidence paths independently of source-tree safety."""
    host = host_classification()
    source = assess_evidence_directory(repo_root, host=host)
    if not live:
        return [
            Finding(
                "INFO",
                "Secure live secret storage",
                "Live secret-storage qualification is deferred until --live; source "
                f"filesystem classification is {source.filesystem_classification}.",
            )
        ]

    secret = assess_secret_file(env_file, host=host)
    evidence = assess_evidence_directory(
        _default_live_evidence_root(repo_root),
        host=host,
    )
    findings = [
        _runtime_path_finding(
            "Secure live secret storage",
            secret,
            "Use TSW_INSTALL_ENV_FILE to point at a WSL-native 0600 secret file.",
        ),
        _runtime_path_finding(
            "Secure live evidence storage",
            evidence,
            "Use XDG_STATE_HOME on the WSL-native filesystem for protected evidence.",
        ),
    ]
    if source.filesystem_classification == "windows_mounted":
        findings.insert(
            0,
            Finding(
                "INFO",
                "Source-tree filesystem",
                "The source tree is Windows-mounted; this is allowed only when "
                "secret and evidence storage pass their independent native checks.",
            ),
        )
    return findings


def _runtime_path_finding(title: str, assessment, remediation: str) -> Finding:
    safe = assessment.to_safe_dict()
    if assessment.allowed:
        return Finding("OK", title, "; ".join(f"{key}={value}" for key, value in safe.items()))
    reasons = ",".join(assessment.reasons()) or "qualification_failed"
    return Finding(
        "FAIL",
        title,
        f"Secure runtime path qualification failed ({reasons}); path contents were not read.",
        (
            remediation,
            "Suggested WSL command: install -d -m 700 \"$HOME/.local/state/tiny-swarm-world\"; "
            "export TSW_INSTALL_ENV_FILE=\"$HOME/.local/state/tiny-swarm-world/live-installation.env\"; "
            "chmod 600 \"$TSW_INSTALL_ENV_FILE\"",
        ),
    )


def _resolve_env_file(repo_root: Path, configured: str | None) -> Path:
    value = configured or os.environ.get("TSW_INSTALL_ENV_FILE") or SECRET_ENV_FILE
    path = Path(value).expanduser()
    return path if path.is_absolute() else repo_root / path


def _default_live_evidence_root(repo_root: Path) -> Path:
    configured_root = os.environ.get("TSW_LIVE_EVIDENCE_ROOT", "").strip()
    if configured_root:
        return Path(configured_root).expanduser()
    configured = os.environ.get("XDG_STATE_HOME", "").strip()
    state_root = Path(configured).expanduser() if configured else Path.home() / ".local" / "state"
    return state_root / "tiny-swarm-world" / "evidence" / "installation-tests"


def _filesystem_permission_findings(repo_root: Path) -> list[Finding]:
    uid = os.geteuid()
    gid = os.getegid()
    owner_mismatches: list[str] = []
    unreadable_files: list[str] = []
    unwritable_dirs: list[str] = []
    non_executable_shell_scripts: list[str] = []

    for path in _walk_selected_paths(repo_root, PERMISSION_SCAN_PATHS):
        try:
            path_stat = path.stat()
        except OSError:
            continue
        relative_path = path.relative_to(repo_root).as_posix()
        if path_stat.st_uid != uid or path_stat.st_gid != gid:
            owner_mismatches.append(relative_path)
        if path.is_dir() and not os.access(path, os.W_OK):
            unwritable_dirs.append(relative_path)
        if path.is_file() and not os.access(path, os.R_OK):
            unreadable_files.append(relative_path)
        if path.is_file() and path.suffix == ".sh" and not os.access(path, os.X_OK):
            non_executable_shell_scripts.append(relative_path)

    return [
        _count_finding("Owner mismatch", owner_mismatches, "WARN", _chown_hint(repo_root)),
        _count_finding("Unreadable files", unreadable_files, "FAIL", ()),
        _count_finding("Unwritable directories", unwritable_dirs, "WARN", ()),
        _count_finding(
            "Shell scripts without execute bit",
            non_executable_shell_scripts,
            "WARN",
            ("Run targeted chmod only for scripts you execute, for example: chmod u+x install.sh",),
        ),
    ]


def _secret_file_mode_finding(
    secret_file: Path,
    *,
    live: bool,
    fix_permissions: bool,
) -> Finding:
    if not secret_file.exists():
        return Finding("INFO", SECRET_FILE_MODE_LABEL, f"{SECRET_ENV_FILE} does not exist yet.")

    mode = stat.S_IMODE(secret_file.stat().st_mode)
    if not mode & 0o077:
        return Finding("OK", SECRET_FILE_MODE_LABEL, f"{SECRET_ENV_FILE} is private.")
    if live and fix_permissions:
        if host_classification() == "wsl2" and secret_file.as_posix().startswith("/mnt/"):
            return Finding(
                "FAIL",
                SECRET_FILE_MODE_LABEL,
                "A Windows-mounted secret file cannot be repaired into a trustworthy "
                "owner-only live secret store.",
                ("Move the secret file to a WSL-native filesystem and set TSW_INSTALL_ENV_FILE.",),
            )
        secret_file.chmod(0o600)
        try:
            secret_file.parent.chmod(0o700)
        except OSError:
            return Finding(
                "FAIL",
                SECRET_FILE_MODE_LABEL,
                "The secret directory mode could not be verified safely.",
                ("Create the secret directory on a WSL-native filesystem with mode 0700.",),
            )
        return Finding("FIXED", SECRET_FILE_MODE_LABEL, f"Set {SECRET_ENV_FILE} mode to 0600.")
    return Finding(
        "WARN",
        SECRET_FILE_MODE_LABEL,
        f"{SECRET_ENV_FILE} is {mode:04o}; expected 0600.",
        (f"Run: chmod 600 {SECRET_ENV_FILE}",),
    )


def check_systemd(*, live: bool) -> tuple[SystemdState, list[Finding]]:
    pid1 = _read_text(Path("/proc/1/comm")).strip() or "unknown"
    wsl = bool(os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"))
    osrelease = _read_text(Path("/proc/sys/kernel/osrelease")).casefold()
    if "microsoft" in osrelease or "wsl" in osrelease:
        wsl = True
    available = pid1 == "systemd" and Path("/run/systemd/system").is_dir()
    wsl_conf_systemd = _wsl_conf_systemd_state()
    systemctl_state = ""
    if live and shutil.which("systemctl"):
        systemctl_state = _run_text(("systemctl", "is-system-running", "--no-pager"))

    state = SystemdState(
        wsl=wsl,
        available=available,
        pid1=pid1,
        wsl_conf_systemd=wsl_conf_systemd,
        systemctl_state=systemctl_state.strip(),
    )
    findings = [
        Finding(
            "INFO",
            "WSL detection",
            "WSL indicators are present." if wsl else "No WSL indicator was detected.",
        )
    ]
    if available:
        findings.append(
            Finding(
                "OK",
                "systemd availability",
                _systemd_detail(state),
            )
        )
    else:
        findings.append(
            Finding(
                "FAIL" if wsl else "WARN",
                "systemd availability",
                _systemd_detail(state),
                (
                    "For WSL2, enable systemd in /etc/wsl.conf with [boot] systemd=true, "
                    "then restart the WSL distribution.",
                    "Without systemd, systemd unit files and journalctl unit logs are unavailable.",
                ),
            )
        )
    return state, findings


def check_service_definitions(repo_root: Path, systemd_state: SystemdState) -> list[Finding]:
    units = tuple(_unit_files(repo_root))
    if not units:
        return [
            Finding(
                "INFO",
                "systemd unit definitions",
                "No .service/.socket/.timer files were found in the repository.",
            )
        ]

    findings: list[Finding] = []
    for unit in units:
        relative_path = unit.relative_to(repo_root).as_posix()
        text = unit.read_text(encoding="utf-8", errors="replace")
        issues = _unit_compatibility_issues(text, systemd_state)
        if issues:
            findings.append(
                Finding(
                    "WARN" if systemd_state.available else "FAIL",
                    f"Unit compatibility: {relative_path}",
                    "; ".join(issues),
                    (
                        "Prefer Tiny Swarm World setup workflows over host systemd units "
                        "when running under WSL without systemd.",
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    "OK",
                    f"Unit compatibility: {relative_path}",
                    "No WSL/systemd compatibility issue was detected.",
                )
            )
    return findings


def check_latest_evidence(repo_root: Path) -> list[Finding]:
    evidence_dir = latest_evidence_dir(repo_root)
    if evidence_dir is None:
        return [
            Finding(
                "INFO",
                "Installation evidence",
                f"No evidence directory found under {EVIDENCE_ROOT}.",
            )
        ]
    context = evidence_dir / "context.txt"
    details = [f"Latest evidence: {evidence_dir.relative_to(repo_root).as_posix()}"]
    for name in ("reset-run.exit", "setup-run.exit"):
        exit_file = evidence_dir / name
        if exit_file.exists():
            details.append(f"{name}={exit_file.read_text(encoding='utf-8').strip()}")
    if context.exists():
        details.append("context.txt present")
    return [Finding("INFO", "Installation evidence", "; ".join(details))]


def log_guidance(repo_root: Path) -> tuple[str, ...]:
    evidence_dir = latest_evidence_dir(repo_root)
    evidence_ref = (
        evidence_dir.relative_to(repo_root).as_posix()
        if evidence_dir is not None
        else EVIDENCE_ROOT + "/<host-runtime>/<UTC timestamp>"
    )
    return (
        f"EVIDENCE={evidence_ref}",
        'tail -n 120 "$EVIDENCE/reset-run.log"',
        'tail -n 120 "$EVIDENCE/setup-run.log"',
        'grep -n -i "service" "$EVIDENCE/reset-run.log" "$EVIDENCE/setup-run.log" | tail -n 80',
        (
            'line=$(grep -n -i "service" "$EVIDENCE/setup-run.log" | tail -n 1 | cut -d: -f1); '
            'test -n "$line" && sed -n "$((line > 30 ? line - 30 : 1)),$((line + 80))p" '
            '"$EVIDENCE/setup-run.log"'
        ),
        "systemctl --failed --no-pager",
        "journalctl --no-pager -u '<unit>.service' --since 'today'",
        "journalctl --no-pager -b | grep -i 'service'",
    )


def print_report(repo_root: Path, findings: list[Finding], guidance: tuple[str, ...]) -> None:
    print("Tiny Swarm World installation debugger")
    print(f"Repository: {repo_root}")
    print()
    for finding in sorted(findings, key=lambda item: STATUS_ORDER[item.status]):
        print(f"[{finding.status}] {finding.title}")
        print(f"  {finding.detail}")
        for remediation in finding.remediation:
            print(f"  -> {remediation}")
    print()
    print("Service log drill-down")
    for command in guidance:
        print(f"  {command}")


def latest_evidence_dir(repo_root: Path) -> Path | None:
    root = repo_root / EVIDENCE_ROOT
    if not root.is_dir():
        return None
    candidates = tuple(_evidence_run_directories(root))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.name)


def _evidence_run_directories(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for host_directory in SUPPORTED_EVIDENCE_HOST_DIRECTORIES:
        host_root = root / host_directory
        if host_root.is_dir():
            candidates.extend(path for path in host_root.iterdir() if path.is_dir())
    candidates.extend(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name[:4].isdigit()
    )
    return tuple(candidates)


def _unit_compatibility_issues(text: str, systemd_state: SystemdState) -> tuple[str, ...]:
    issues: list[str] = []
    if not systemd_state.available:
        issues.append("systemd is not available, so this unit cannot be managed in WSL")
    lowered = text.casefold()
    if "powershell.exe" in lowered or "cmd.exe" in lowered or re.search(r"[a-z]:\\\\", lowered):
        issues.append("unit contains Windows-native command references")
    if "network-online.target" in lowered:
        issues.append("unit depends on network-online.target, which is often fragile in WSL")
    for exec_value in re.findall(r"(?m)^Exec(?:Start|Stop|Reload)=([^\n]+)", text):
        command = exec_value.strip().split(maxsplit=1)[0]
        if command and not command.startswith(("/", "-", "+", "!", "@")):
            issues.append(f"unit command is not absolute: {command}")
    return tuple(dict.fromkeys(issues))


def _unit_files(repo_root: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in _walk_selected_paths(repo_root, UNIT_SCAN_PATHS)
        if path.is_file() and path.name.endswith(UNIT_SUFFIXES)
    )


def _walk_selected_paths(repo_root: Path, relative_paths: tuple[str, ...]):
    seen: set[Path] = set()
    for relative_path in relative_paths:
        path = repo_root / relative_path
        if not path.exists():
            continue
        if path in seen:
            continue
        seen.add(path)
        if relative_path == ".":
            yield path
            continue
        if path.is_file():
            yield path
            continue
        yield from _walk_tree(path, seen)


def _walk_tree(root_path: Path, seen: set[Path]):
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [item for item in dirs if item not in EXCLUDED_SCAN_DIRS]
        current = Path(root)
        if current not in seen:
            seen.add(current)
            yield current
        for name in files:
            path = current / name
            if path in seen:
                continue
            seen.add(path)
            yield path


def _count_finding(
    title: str,
    values: list[str],
    problem_status: Literal["WARN", "FAIL"],
    remediation: tuple[str, ...],
) -> Finding:
    if not values:
        return Finding("OK", title, "No matching problem found.")
    examples = ", ".join(values[:8])
    suffix = "" if len(values) <= 8 else f", ... ({len(values)} total)"
    return Finding(
        problem_status,
        title,
        f"Found {len(values)} item(s): {examples}{suffix}",
        remediation,
    )


def _chown_hint(repo_root: Path) -> tuple[str, ...]:
    user = pwd.getpwuid(os.geteuid()).pw_name
    return (f"Review ownership. If this checkout is yours: sudo chown -R {user}:{user} {repo_root}",)


def _systemd_detail(state: SystemdState) -> str:
    parts = [f"PID 1 is {state.pid1!r}", f"/etc/wsl.conf systemd={state.wsl_conf_systemd}"]
    if state.systemctl_state:
        parts.append(f"systemctl is-system-running: {state.systemctl_state}")
    return "; ".join(parts)


def _wsl_conf_systemd_state() -> str:
    text = _read_text(Path("/etc/wsl.conf"))
    if not text:
        return "unknown"
    in_boot = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_boot = line[1:-1].strip().casefold() == "boot"
            continue
        if in_boot and line.casefold().replace(" ", "") == "systemd=true":
            return "true"
    return "false"


def _run_text(command: tuple[str, ...]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return exc.__class__.__name__
    return (result.stdout or result.stderr).strip()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
