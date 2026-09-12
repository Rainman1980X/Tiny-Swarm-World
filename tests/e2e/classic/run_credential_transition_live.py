"""Explicitly authorized Jenkins transition checks; emit value-free evidence only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import copy
import subprocess
import time
from datetime import UTC, datetime
from typing import Any

import requests

from tiny_swarm_world.application.services.credential_resolution import CredentialResolutionService
from tiny_swarm_world.domain.configuration.credential_resolution import CredentialSource
from tiny_swarm_world.domain.configuration.internal_test_credentials import internal_test_catalog
from tiny_swarm_world.infrastructure.adapters.clients.infisical_cli_client import InfisicalCliClient
from tiny_swarm_world.simple_installer import _prepare_bootstrap_environment
from tools.live.secure_runtime_paths import ensure_secure_directory
from tests.e2e.classic.test_post_install_browser_live import _load_shell_environment

KEY = "TSW_JENKINS_ADMIN_PASSWORD"
PROJECT = {"project": "tiny-swarm-world", "environment": "local"}
URL = "http://localhost:11080"


def identity(session: requests.Session, value: str | None = None) -> tuple[bool, int]:
    """Return only authentication outcome and status, never response data."""
    try:
        response = session.get(
            URL + "/whoAmI/api/json", auth=("admin", value) if value else None, timeout=15,
        )
        payload = response.json() if response.status_code == 200 else {}
        return (payload.get("authenticated") is True and payload.get("name") == "admin", response.status_code)
    except (requests.RequestException, ValueError):
        return False, 0


def wait_identity(value: str) -> bool:
    deadline = time.monotonic() + 180
    with requests.Session() as session:
        while time.monotonic() < deadline:
            if identity(session, value)[0]:
                return True
            time.sleep(3)
    return False


def services() -> dict[str, Any]:
    """Keep secret-bearing specifications in memory for equality comparison."""
    ids = subprocess.check_output(
        ["incus", "exec", "swarm-manager", "--", "docker", "service", "ls", "-q"],
        text=True, timeout=30,
    ).split()
    raw = subprocess.check_output(
        ["incus", "exec", "swarm-manager", "--", "docker", "service", "inspect", *ids],
        text=True, timeout=30,
    )
    return {item["Spec"]["Name"]: item["Spec"] for item in json.loads(raw)}


def deployment_source(raw: bytes) -> str | None:
    """Extract only the verified source label from canonical deployment evidence."""
    try:
        payload = json.loads(raw)
        matches = [item for item in payload.get("verification_results", [])
                   if item.get("target_id") == "deployment:jenkins-stack"
                   and item.get("status") == "verified"]
        source = matches[0].get("evidence", {}).get("resolved_sources") if len(matches) == 1 else None
        return source if source in {item.value for item in CredentialSource} else None
    except (ValueError, AttributeError, TypeError):
        return None


def runtime_value(snapshot: dict[str, Any]) -> str:
    entries = snapshot["jenkins_jenkins"]["TaskTemplate"]["ContainerSpec"]["Env"]
    values = [entry.split("=", 1)[1] for entry in entries if entry.startswith(KEY + "=")]
    require(len(values) == 1, "single_runtime_value_required")
    return values[0]


def operation(environment: dict[str, str], *action: str, observed: dict[str, object] | None = None) -> int:
    command = [sys.executable, "-m", "tiny_swarm_world", "--live", "--approve-live", "--json", "--service-profile", "service-access",
               "--allow-wsl-windows-filesystem", *action]
    with subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=True) as process:
        try:
            stdout, _ = process.communicate(timeout=1200)
            if observed is not None:
                observed["consumed_source"] = deployment_source(stdout)
            return process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=15)
            return 124


def require(condition: object, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


def require_persistent_jenkins_home(snapshot: dict[str, Any]) -> None:
    """Prevent the credential test from replacing an unmigrated anonymous home."""
    mounts = snapshot.get("jenkins_jenkins", {}).get("TaskTemplate", {}).get("ContainerSpec", {}).get("Mounts", [])
    require(any(m.get("Type") == "volume" and m.get("Source") == "jenkins_jenkins_home"
                and m.get("Target") == "/var/jenkins_home" for m in mounts), "jenkins_home_migration_required")


def comparable(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Exclude only the intentional task-restart counter, not service settings."""
    result = copy.deepcopy(snapshot)
    if "jenkins_jenkins" in result:
        result["jenkins_jenkins"]["TaskTemplate"].pop("ForceUpdate", None)
    return result


def updates_settled() -> bool:
    """Do not overlap rollback with updates already accepted by the daemon."""
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            ids = subprocess.check_output(["incus", "exec", "swarm-manager", "--", "docker", "service", "ls", "-q"], text=True, timeout=20).split()
            raw = subprocess.check_output(["incus", "exec", "swarm-manager", "--", "docker", "service", "inspect", *ids], text=True, timeout=20)
            if all(item.get("UpdateStatus", {}).get("State") not in ("updating", "rollback_started") for item in json.loads(raw)):
                return True
        except (subprocess.SubprocessError, ValueError):
            return False
        time.sleep(3)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-live", action="store_true")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scenario", choices=("matching-override", "vault-only", "conflicting-sources"),
                        default="matching-override")
    args = parser.parse_args()
    if not args.approve_live:
        parser.error("--approve-live is required")
    if not args.env_file.is_file() or args.env_file.stat().st_mode & 0o077:
        parser.error("a protected existing environment file is required")
    root = Path.home() / ".local/state/tiny-swarm-world/evidence/cred09-transitions"
    ensure_secure_directory(root)
    run = root / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ensure_secure_directory(run)
    events: list[dict[str, object]] = []
    report: dict[str, object] = {
        "started_utc": datetime.now(UTC).isoformat(),
        "candidate": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_modified": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "host": "wsl2" if "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower() else "native_linux",
        "operations": events, "status": "LIVE_PARTIAL", "approve_live": True,
        "scenario": args.scenario, "profile": "service-access",
        "command": "python -m tests.e2e.classic.run_credential_transition_live --approve-live --env-file <protected> --scenario " + args.scenario,
        "runner_sha256": __import__("hashlib").sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    def record(name: str, **outcomes: object) -> None:
        events.append({"operation": name, "utc": datetime.now(UTC).isoformat(), **outcomes})
        (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"operation": name, **outcomes}), flush=True)

    base = {**os.environ, **_load_shell_environment(args.env_file), "TSW_INSTALL_ENV_FILE": str(args.env_file),
            "TSW_LIVE_EVIDENCE_ROOT": str(run)}
    configured_baseline = _prepare_bootstrap_environment(base, Path.cwd())
    require(configured_baseline[KEY] == internal_test_catalog().resolve(KEY), "catalog_baseline_required")
    baseline = _prepare_bootstrap_environment({**base, KEY: ""}, Path.cwd())
    os.environ.update(baseline)
    client = InfisicalCliClient()
    resolver = CredentialResolutionService()
    keys = tuple(json.loads(baseline["TSW_CREDENTIAL_SOURCE_MAP"]))
    vault_before = {key: client.get_secret(key, **PROJECT) for key in keys}
    original = baseline[KEY]
    old_vault = vault_before[KEY]
    if not old_vault or old_vault != original or not wait_identity(original):
        record("preflight", passed=False, reason="baseline_or_rollback_mismatch")
        return 1
    before = services()
    require(runtime_value(before) == original, "baseline_runtime_value_mismatch")
    require_persistent_jenkins_home(before)
    require(updates_settled(), "preflight_updates_not_settled")
    custom = secrets.token_urlsafe(32)
    operator_input = ("" if args.scenario == "vault-only" else
                      secrets.token_urlsafe(32) if args.scenario == "conflicting-sources" else custom)
    candidate_inputs = {**base, KEY: operator_input}
    custom_environment = _prepare_bootstrap_environment(candidate_inputs, Path.cwd())
    before_snapshot = resolver.resolve_post_bootstrap((KEY,), secure_values={KEY: old_vault})
    after_snapshot = resolver.resolve_post_bootstrap(
        (KEY,), operator_values=({KEY: operator_input} if operator_input else None), secure_values={KEY: custom})
    comparison = after_snapshot.compare_to(before_snapshot)
    require(comparison.changed_keys == (KEY,), "unexpected_resolution_drift")
    baseline_sources = json.loads(baseline["TSW_CREDENTIAL_SOURCE_MAP"])
    override_sources = json.loads(custom_environment["TSW_CREDENTIAL_SOURCE_MAP"])
    require(all(baseline_sources[k] == override_sources[k] for k in keys if k != KEY), "unrelated_source_drift")
    require(override_sources[KEY] == ("default" if args.scenario == "vault-only" else "operator"),
            "unexpected_bootstrap_source")
    record("source_resolution", bootstrap_source=override_sources[KEY], selected_source=after_snapshot.sources[KEY].value,
           distinct_operator_and_vault=bool(operator_input) and operator_input != custom,
           independent_vault_change=args.scenario == "vault-only", only_intended_key_changed=True)
    cookie_session = requests.Session()
    private = Path.home() / ".local/state/tiny-swarm-world/cred09-rollback"
    ensure_secure_directory(private)
    rollback = private / (run.name + ".json")
    with os.fdopen(os.open(rollback, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        json.dump({"key": KEY, "operator": original, "vault": old_vault, "service_specs": before,
                   "baseline_environment": baseline}, handle)
    passed = False
    restored = False
    try:
        before_readiness = operation(baseline, "deployment", "verify")
        record("before_readiness", exit_code=before_readiness)
        require(before_readiness == 0, "baseline_services_not_ready")
        baseline_observed: dict[str, object] = {}
        baseline_code = operation(baseline, "deployment", "apply", observed=baseline_observed)
        baseline_equal = services() == before
        baseline_authenticated = wait_identity(original)
        record("baseline_deployment", exit_code=baseline_code, service_specs_equal=baseline_equal,
               consumed_source=baseline_observed.get("consumed_source"), authenticated=baseline_authenticated,
               bootstrap_source=json.loads(baseline["TSW_CREDENTIAL_SOURCE_MAP"])[KEY], catalog_value_confirmed=True)
        require(baseline_code == 0 and baseline_equal and baseline_authenticated and baseline_observed.get("consumed_source") == "vault",
                "baseline_deployment_not_verified")
        cookie_session.get(URL + "/login", timeout=15).raise_for_status()
        login = cookie_session.post(URL + "/j_spring_security_check",
                                    data={"j_username": "admin", "j_password": original, "from": "/", "Submit": "Sign in"}, timeout=20)
        del login
        require(identity(cookie_session)[0], "session_precondition_failed")
        record("baseline_session", authenticated=True)
        client.set_secret(KEY, custom, **PROJECT)
        started = time.monotonic()
        consumed: dict[str, object] = {}
        code = operation(custom_environment, "deployment", "apply", observed=consumed)
        new_ok = wait_identity(custom) if code == 0 else False
        with requests.Session() as session:
            old_ok, old_status = identity(session, original)
        with requests.Session() as session:
            operator_ok, operator_status = identity(session, operator_input or custom_environment[KEY])
        session_ok, session_status = identity(cookie_session)
        after_services = services()
        before_comparable, after_comparable = before, after_services
        changed_services = sorted(name for name in set(before) | set(after_services)
                                  if before_comparable.get(name) != after_comparable.get(name))
        vault_now = {key: client.get_secret(key, **PROJECT) for key in keys}
        changed_vault = sorted(key for key in keys if vault_now[key] != vault_before[key])
        record("override", exit_code=code, duration_seconds=round(time.monotonic() - started, 3), new_identity_authenticated=new_ok,
               old_identity_rejected=not old_ok and old_status in (401, 403), old_status=old_status,
               previous_cookie_authenticated=session_ok, previous_cookie_status=session_status,
               session_scope="credential_update_and_task_replacement",
               changed_services=changed_services, changed_vault_keys=changed_vault,
               consumed_source=consumed.get("consumed_source"), runtime_value_equals_selected=runtime_value(after_services) == custom,
               non_effective_input_rejected=(not operator_ok and operator_status in (401, 403))
               if args.scenario != "matching-override" else None)
        require(code == 0 and new_ok and not old_ok and old_status in (401, 403), "override_authentication_failed")
        require(consumed.get("consumed_source") == "vault" and runtime_value(after_services) == custom,
                "consumer_did_not_receive_selected_vault_value")
        if args.scenario != "matching-override":
            require(not operator_ok and operator_status in (401, 403), "non_effective_input_authenticated")
        require(not session_ok and session_status in (200, 401, 403), "old_session_not_invalidated")
        require(changed_services == ["jenkins_jenkins"] and changed_vault == [KEY], "unrelated_state_changed")
        reconcile = operation(custom_environment, "platform", "reconcile")
        require(reconcile == 0 and wait_identity(custom), "reconcile_failed")
        stable_vault = all(client.get_secret(key, **PROJECT) == vault_now[key] for key in keys)
        stable_services = services() == after_services
        stable_sources = json.loads(_prepare_bootstrap_environment(candidate_inputs, Path.cwd())["TSW_CREDENTIAL_SOURCE_MAP"]) == override_sources
        record("reconcile", exit_code=reconcile, values_equal=stable_vault, authenticated=True,
               service_specs_equal=stable_services, sources_equal=stable_sources)
        require(stable_vault and stable_services and stable_sources, "reconcile_drift")
        repeated: dict[str, object] = {}
        reapply = operation(custom_environment, "deployment", "apply", observed=repeated)
        reapply_equal = services() == after_services
        require(reapply == 0 and repeated.get("consumed_source") == consumed.get("consumed_source")
                and reapply_equal and wait_identity(custom), "redeployment_drift")
        record("redeployment", exit_code=reapply, service_specs_equal=reapply_equal,
               consumed_source=repeated.get("consumed_source"), authenticated=True)
        task_command = ["incus", "exec", "swarm-manager", "--", "docker", "ps", "-q",
                        "--filter", "label=com.docker.swarm.service.name=jenkins_jenkins"]
        old_tasks = subprocess.check_output(task_command, text=True, timeout=20).split()
        require(len(old_tasks) == 1, "single_jenkins_task_required")
        old_task = old_tasks[0]
        restarted = subprocess.run(["incus", "exec", "swarm-manager", "--", "docker", "service", "update",
                                    "--detach=true", "--force", "jenkins_jenkins"], capture_output=True, timeout=60, check=False)
        deadline = time.monotonic() + 180
        new_task = old_task
        while time.monotonic() < deadline:
            new_tasks = subprocess.check_output(task_command, text=True, timeout=20).split()
            new_task = new_tasks[0] if len(new_tasks) == 1 else old_task
            if new_task and new_task != old_task:
                break
            time.sleep(3)
        restarted_ok = restarted.returncode == 0 and bool(new_task) and new_task != old_task and updates_settled() and wait_identity(custom)
        restart_equal = comparable(services()) == comparable(after_services)
        restart_vault_equal = all(client.get_secret(key, **PROJECT) == vault_now[key] for key in keys)
        restart_sources_equal = json.loads(_prepare_bootstrap_environment(candidate_inputs, Path.cwd())["TSW_CREDENTIAL_SOURCE_MAP"]) == override_sources
        record("controlled_jenkins_restart", exit_code=restarted.returncode,
               authenticated=restarted_ok, task_replaced=bool(new_task) and new_task != old_task, service_specs_equal=restart_equal,
               vault_values_equal=restart_vault_equal, sources_equal=restart_sources_equal,
               runtime_value_equals_selected=runtime_value(services()) == custom,
               source_provenance="unchanged service specification from verified deployment")
        require(restarted_ok and restart_equal and restart_vault_equal and restart_sources_equal, "restart_failed")
        passed = True
    except Exception as error:
        record("transition_failure", classification=type(error).__name__)
    finally:
        if not updates_settled():
            report["status"] = "LIVE_FAILED_AFTER_MUTATION"
            record("restore_blocked", reason="daemon_updates_not_settled", protected_rollback_retained=True)
            cookie_session.close()
            raise RuntimeError("restore_blocked_unsettled_daemon_updates")
        try:
            client.set_secret(KEY, old_vault, **PROJECT)
            record("restore_vault", completed=True)
        except Exception as error:
            record("restore_vault", completed=False, classification=type(error).__name__)
        try:
            restored_source: dict[str, object] = {}
            code = operation(baseline, "deployment", "apply", observed=restored_source)
            restored = code == 0 and wait_identity(original)
            with requests.Session() as session:
                custom_ok, custom_status = identity(session, custom)
            vault_equal = all(client.get_secret(key, **PROJECT) == vault_before[key] for key in keys)
            final_services = services()
            services_equal = comparable(before) == comparable(final_services)
            restored = (restored and not custom_ok and custom_status in (401, 403) and vault_equal and services_equal
                        and restored_source.get("consumed_source") == "vault")
            record("restore", exit_code=code, authenticated=wait_identity(original), override_rejected=not custom_ok,
                   vault_values_equal=vault_equal, service_specs_equal=services_equal, complete=restored,
                   consumed_source=restored_source.get("consumed_source"))
            if restored:
                readiness = operation(baseline, "deployment", "verify")
                record("after_readiness", exit_code=readiness)
                restored = readiness == 0
            if restored:
                rollback.unlink()
                record("cleanup", temporary_secret_removed=True)
        except Exception as error:
            record("restore_failure", classification=type(error).__name__, protected_rollback_retained=True)
        cookie_session.close()
    report["status"] = "LIVE_VERIFIED" if passed and restored else "LIVE_FAILED_AFTER_MUTATION"
    report["scope"] = "Jenkins post-bootstrap source precedence and startup consumer; no general rotation API"
    report["finished_utc"] = datetime.now(UTC).isoformat()
    report["duration_seconds"] = round((datetime.fromisoformat(str(report["finished_utc"]))
                                         - datetime.fromisoformat(str(report["started_utc"]))).total_seconds(), 3)
    (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "evidence": str(run)}), flush=True)
    return 0 if passed and restored else 1


if __name__ == "__main__":
    raise SystemExit(main())
