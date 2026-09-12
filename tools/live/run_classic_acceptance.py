#!/usr/bin/env python3
"""Run the authorized Classic live chain and write only redacted evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.live.secure_runtime_paths import (  # noqa: E402
    RuntimePathAssessment,
    assess_evidence_directory,
    assess_secret_file,
    ensure_secure_directory,
    host_classification,
)

DEFAULT_ENV_FILE = REPOSITORY_ROOT / ".tiny-swarm-world/local/live-installation.env"
EVIDENCE_ROOT = (
    Path(os.environ["TSW_LIVE_EVIDENCE_ROOT"]).expanduser()
    if os.environ.get("TSW_LIVE_EVIDENCE_ROOT", "").strip()
    else (
        Path(os.environ.get("XDG_STATE_HOME", "")).expanduser()
        if os.environ.get("XDG_STATE_HOME", "").strip()
        else Path.home() / ".local" / "state"
    ) / "tiny-swarm-world" / "evidence" / "live-greenpath"
)
TEST_COUNT_PATTERN = re.compile(r"Ran (\d+) tests? in ([0-9.]+)s")
SKIP_PATTERN = re.compile(r"skipped=(\d+)")


@dataclass(frozen=True)
class CommandResult:
    operation: str
    started_at: str
    finished_at: str
    duration_seconds: float
    exit_code: int
    summary: dict[str, object]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-live", action="store_true")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    parser.add_argument(
        "--credential-rotation-reference",
        help="Non-secret reference proving the previously exposed credential was rotated or revoked.",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Run the disposable test profile; credential rotation is not applicable.",
    )
    parser.add_argument("--update-stack", default=os.environ.get("TSW_CLASSIC_UPDATE_STACK"))
    parser.add_argument("--update-service", default=os.environ.get("TSW_CLASSIC_UPDATE_SERVICE"))
    parser.add_argument("--update-from-image", default=os.environ.get("TSW_CLASSIC_UPDATE_FROM_IMAGE"))
    parser.add_argument("--update-to-image", default=os.environ.get("TSW_CLASSIC_UPDATE_TO_IMAGE"))
    args = parser.parse_args()

    started_at = _utc_now()
    run_id = started_at.replace("-", "").replace(":", "").replace("+00:00", "Z")
    env_file = _resolve_env_file(args.env_file)
    try:
        evidence_storage = ensure_secure_directory(args.evidence_root)
        evidence_dir = args.evidence_root / run_id
        ensure_secure_directory(evidence_dir)
    except (OSError, RuntimeError):
        return 1

    if not args.approve_live:
        return _write_terminal_result(
            evidence_dir,
            run_id=run_id,
            started_at=started_at,
            status="LIVE_CONSENT_MISSING",
            operations=(),
            reason="--approve-live was not supplied",
            source_filesystem=None,
            secret_storage=None,
            evidence_storage=evidence_storage,
            credential_rotation_reference=None,
            test_only=args.test_only,
        )

    if not env_file.is_file():
        return _write_terminal_result(
            evidence_dir,
            run_id=run_id,
            started_at=started_at,
            status="LIVE_PREREQUISITE_MISSING",
            operations=(),
            reason="live environment source is missing",
            source_filesystem=None,
            secret_storage=None,
            evidence_storage=evidence_storage,
            credential_rotation_reference=None,
            test_only=args.test_only,
        )

    if not _rotation_reference_valid_for_profile(
        args.test_only, args.credential_rotation_reference
    ):
        return _write_terminal_result(
            evidence_dir,
            run_id=run_id,
            started_at=started_at,
            status="LIVE_PREREQUISITE_MISSING",
            operations=(),
            reason="credential rotation or revocation reference is missing or invalid",
            source_filesystem=None,
            secret_storage=None,
            evidence_storage=evidence_storage,
            credential_rotation_reference=None,
            test_only=args.test_only,
        )

    source_filesystem = assess_evidence_directory(
        REPOSITORY_ROOT,
        host=host_classification(),
    )
    secret_storage = assess_secret_file(
        env_file,
        host=host_classification(),
    )
    if (
        source_filesystem.filesystem_classification == "unknown"
        or not secret_storage.allowed
    ):
        return _write_terminal_result(
            evidence_dir,
            run_id=run_id,
            started_at=started_at,
            status="LIVE_BLOCKED_BEFORE_MUTATION",
            operations=(),
            reason="source or mutable secret storage failed secure-path qualification",
            source_filesystem=source_filesystem,
            secret_storage=secret_storage,
            evidence_storage=evidence_storage,
            credential_rotation_reference=args.credential_rotation_reference,
            test_only=args.test_only,
        )

    update_values = (
        args.update_stack,
        args.update_service,
        args.update_from_image,
        args.update_to_image,
    )
    if any(not value or not value.strip() for value in update_values):
        return _write_terminal_result(
            evidence_dir,
            run_id=run_id,
            started_at=started_at,
            status="LIVE_PREREQUISITE_MISSING",
            operations=(),
            reason="canonical update stack, service and source/target images are required",
            source_filesystem=source_filesystem,
            secret_storage=secret_storage,
            evidence_storage=evidence_storage,
            credential_rotation_reference=args.credential_rotation_reference,
            test_only=args.test_only,
        )

    environment = os.environ.copy()
    # Keep application-generated preflight evidence inside the runner's
    # already-qualified evidence root, including when the root was selected by
    # the default WSL-native state path rather than an environment override.
    environment["TSW_LIVE_EVIDENCE_ROOT"] = args.evidence_root.resolve().as_posix()
    operations: list[CommandResult] = []
    commands = (
        ("diagnostics", ("python3", "tools/install_debugger.py", "--live"), 120),
        (
            "setup",
            (
                "./tsw",
                "--live",
                "--approve-live",
                "--json",
                "--service-profile",
                "service-access",
                "--allow-wsl-windows-filesystem",
                "setup",
                "run",
            ),
            1800,
        ),
        (
            "platform_verify",
            (
                "./tsw",
                "--json",
                "--service-profile",
                "service-access",
                "--allow-wsl-windows-filesystem",
                "platform",
                "verify",
            ),
            300,
        ),
        (
            "classic_e2e",
            (
                "env",
                "TSW_RUN_POST_INSTALL_BROWSER_LIVE=1",
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/e2e/classic",
                "-t",
                ".",
            ),
            900,
        ),
        (
            "reconcile",
            (
                "./tsw",
                "--live",
                "--approve-live",
                "--json",
                "--service-profile",
                "service-access",
                "platform",
                "reconcile",
            ),
            1800,
        ),
        (
            "reconcile_e2e",
            (
                "env",
                "TSW_RUN_POST_INSTALL_BROWSER_LIVE=1",
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/e2e/classic",
                "-t",
                ".",
            ),
            900,
        ),
        (
            "update",
            (
                "./tsw",
                "--live",
                "--approve-live",
                "--json",
                "--service-profile",
                "service-access",
                "platform",
                "update",
                "--stack",
                args.update_stack.strip(),
                "--service",
                args.update_service.strip(),
                "--from-image",
                args.update_from_image.strip(),
                "--to-image",
                args.update_to_image.strip(),
            ),
            1800,
        ),
        (
            "update_e2e",
            (
                "env",
                "TSW_RUN_POST_INSTALL_BROWSER_LIVE=1",
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/e2e/classic",
                "-t",
                ".",
            ),
            900,
        ),
        (
            "recovery",
            (
                "./tsw",
                "--live",
                "--approve-live",
                "--json",
                "--service-profile",
                "service-access",
                "platform",
                "update",
                "--recover",
                "--stack",
                args.update_stack.strip(),
                "--service",
                args.update_service.strip(),
            ),
            1800,
        ),
        (
            "recovery_e2e",
            (
                "env",
                "TSW_RUN_POST_INSTALL_BROWSER_LIVE=1",
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests/e2e/classic",
                "-t",
                ".",
            ),
            900,
        ),
    )

    status = "LIVE_VERIFIED"
    for operation, command, timeout in commands:
        result = _run_operation(operation, command, timeout, env_file, environment)
        operations.append(result)
        if not _operation_succeeded(result):
            status = "LIVE_PREREQUISITE_MISSING" if operation == "diagnostics" else "LIVE_FAILED_AFTER_MUTATION"
            break

    return _write_terminal_result(
        evidence_dir,
        run_id=run_id,
        started_at=started_at,
        status=status,
        operations=tuple(operations),
        reason=None,
        source_filesystem=source_filesystem,
        secret_storage=secret_storage,
        evidence_storage=evidence_storage,
        credential_rotation_reference=args.credential_rotation_reference,
        test_only=args.test_only,
    )


def _run_operation(
    operation: str,
    command: tuple[str, ...],
    timeout: int,
    env_file: Path,
    environment: dict[str, str],
) -> CommandResult:
    started_at = _utc_now()
    started = monotonic()
    shell_command = f"set -a; . {shlex.quote(env_file.as_posix())}; set +a; exec {shlex.join(command)}"
    try:
        completed = subprocess.run(
            ["bash", "-lc", shell_command],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        exit_code = completed.returncode
        summary = _summarize(operation, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired:
        exit_code = 124
        summary = {"result": "timed_out", "timeout_seconds": timeout}
    except OSError:
        exit_code = 126
        summary = {"result": "execution_error"}
    finished_at = _utc_now()
    return CommandResult(
        operation=operation,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round(monotonic() - started, 3),
        exit_code=exit_code,
        summary=summary,
    )


def _summarize(operation: str, stdout: str, stderr: str) -> dict[str, object]:
    if operation.endswith("_e2e"):
        match = TEST_COUNT_PATTERN.search(stdout + "\n" + stderr)
        skips = SKIP_PATTERN.search(stdout + "\n" + stderr)
        return {
            "result": "passed"
            if "OK" in stdout + stderr and "FAILED" not in stdout + stderr and not skips
            else "failed",
            "tests": int(match.group(1)) if match else None,
            "runtime_seconds": float(match.group(2)) if match else None,
            "skipped": int(skips.group(1)) if skips else 0,
        }
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {"result": "completed_without_structured_summary" if not stderr else "failed"}
    if not isinstance(payload, dict):
        return {"result": "completed_without_structured_summary"}
    outcome = payload.get("outcome")
    outcome_dict = outcome if isinstance(outcome, dict) else {}
    verification_results = outcome_dict.get("verification_results")
    result_count = len(verification_results) if isinstance(verification_results, list) else 0
    return {
        "result": _structured_result(payload),
        "status": payload.get("status"),
        "verification": outcome_dict.get("verification"),
        "mutation": outcome_dict.get("mutation", {}).get("result")
        if isinstance(outcome_dict.get("mutation"), dict)
        else None,
        "result_count": result_count,
    }


def _structured_result(payload: dict[str, object]) -> str:
    status = str(payload.get("status", "")).casefold()
    outcome = payload.get("outcome")
    if isinstance(outcome, dict):
        nested_status = str(outcome.get("status", "")).casefold()
        status = nested_status or status
    if status in {"failed", "blocked", "degraded", "partial", "skipped", "refused"}:
        return status
    return "passed" if status in {"completed", "passed", "verified", "ok"} else "completed"


def _operation_succeeded(result: CommandResult) -> bool:
    if result.exit_code != 0:
        return False
    if result.operation == "diagnostics":
        return result.summary.get("result") not in {
            "failed",
            "blocked",
            "degraded",
            "partial",
            "skipped",
            "refused",
            "timed_out",
            "execution_error",
        }
    return result.summary.get("result") == "passed"


def _write_terminal_result(
    evidence_dir: Path,
    *,
    run_id: str,
    started_at: str,
    status: str,
    operations: tuple[CommandResult, ...],
    reason: str | None,
    source_filesystem: RuntimePathAssessment | None,
    secret_storage: RuntimePathAssessment | None,
    evidence_storage: RuntimePathAssessment,
    credential_rotation_reference: str | None,
    test_only: bool = False,
) -> int:
    finished_at = _utc_now()
    payload = {
        "run_id": run_id,
        "repository_commit": _git_commit(),
        "scenario": "classic_live_chain",
        "execution_profile": "disposable_test" if test_only else "protected_live",
        "host_class": _host_class(),
        "host": {
            "class": _host_class(),
            "kernel_release": platform.release(),
            "pid1": _safe_pid1(),
            "systemd_directory_present": Path("/run/systemd/system").is_dir(),
        },
        "runner": {
            "name": _safe_runner_name(),
            "label": os.environ.get("CLASSIC_LIVE_RUNNER_LABEL", "tsw-classic"),
            "target_owner_reference_present": bool(
                os.environ.get("TSW_CLASSIC_TARGET_OWNER", "").strip()
            ),
        },
        "consent_state": "LIVE_APPROVED" if status != "LIVE_CONSENT_MISSING" else status,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "status": status,
        "reason": reason,
        "source_filesystem": (
            source_filesystem.to_safe_dict() if source_filesystem is not None else {}
        ),
        "secret_storage": (
            secret_storage.to_safe_dict() if secret_storage is not None else {}
        ),
        "evidence_storage": evidence_storage.to_safe_dict(),
        "credential_rotation": {
            "status": _rotation_evidence_status(test_only, credential_rotation_reference),
            "reference_present": (
                bool(credential_rotation_reference) if not test_only else False
            ),
            "reference_value": "not_recorded",
        },
        "operations": [
            {
                "operation": operation.operation,
                "started_at_utc": operation.started_at,
                "finished_at_utc": operation.finished_at,
                "duration_seconds": operation.duration_seconds,
                "exit_code": operation.exit_code,
                "command": _safe_command_label(operation.operation),
                "summary": operation.summary,
            }
            for operation in operations
        ],
        "redaction": "raw stdout, stderr, credentials and environment values were not written",
    }
    summary_path = evidence_dir / "run-summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _private(summary_path)
    checksum_path = evidence_dir / "checksums.sha256"
    digest = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  run-summary.json\n", encoding="utf-8")
    _private(checksum_path)
    checksum_digest = hashlib.sha256(checksum_path.read_bytes()).hexdigest()
    terminal_path = evidence_dir / "checksums.sha256.sha256"
    terminal_path.write_text(f"{checksum_digest}  checksums.sha256\n", encoding="utf-8")
    _private(terminal_path)
    return 0 if status == "LIVE_VERIFIED" else 1


def _resolve_env_file(value: Path | None) -> Path:
    configured = value
    if configured is None:
        configured_text = os.environ.get("TSW_INSTALL_ENV_FILE", "").strip()
        configured = Path(configured_text) if configured_text else DEFAULT_ENV_FILE
    return configured if configured.is_absolute() else REPOSITORY_ROOT / configured


def _safe_command_label(operation: str) -> str:
    return {
        "diagnostics": "python3 tools/install_debugger.py --live",
        "setup": "./tsw --live --approve-live --json setup run",
        "platform_verify": "./tsw --json platform verify",
        "reconcile": "./tsw --live --approve-live --json platform reconcile",
        "update": "./tsw --live --approve-live --json platform update --stack <configured> --service <configured>",
        "classic_e2e": "env TSW_RUN_POST_INSTALL_BROWSER_LIVE=1 python3 -m unittest discover",
        "reconcile_e2e": "env TSW_RUN_POST_INSTALL_BROWSER_LIVE=1 python3 -m unittest discover",
        "update_e2e": "env TSW_RUN_POST_INSTALL_BROWSER_LIVE=1 python3 -m unittest discover",
        "recovery": "./tsw --live --approve-live --json platform update --recover --stack <configured> --service <configured>",
        "recovery_e2e": "env TSW_RUN_POST_INSTALL_BROWSER_LIVE=1 python3 -m unittest discover",
    }.get(operation, operation)


def _valid_rotation_reference(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{1,127}", value))


def _rotation_reference_valid_for_profile(test_only: bool, value: str | None) -> bool:
    return test_only or _valid_rotation_reference(value)


def _rotation_evidence_status(test_only: bool, value: str | None) -> str:
    if test_only:
        return "not_applicable_test_only"
    return "recorded" if value else "not_recorded"


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _host_class() -> str:
    if Path("/run/WSL").exists() or "microsoft" in platform.release().casefold():
        return "wsl2"
    return "native_linux"


def _safe_pid1() -> str:
    try:
        return Path("/proc/1/comm").read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unavailable"


def _safe_runner_name() -> str:
    value = os.environ.get("RUNNER_NAME", "").strip()
    return value if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value) else "unknown"


def _private(path: Path) -> None:
    path.chmod(0o700 if path.is_dir() else 0o600)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
