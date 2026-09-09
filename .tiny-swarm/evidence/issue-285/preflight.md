# Live Preflight: #285 / CRED-07

## Authorized live continuation: 2026-09-09

Publication handoff: PR #293 merged outside this execution at 05:22:23 UTC,
before the new evidence was published. The reviewed evidence commit was
therefore transferred to isolated branch
`feature/cred-07-wsl-evidence-20260909` from current main `9788b0eb`.
The intervening #303 changes affect documentation only; Python/configuration
matches the live-tested `7380f751` candidate. No unrelated changes are included
in the evidence follow-up.

The user explicitly granted all permissions required to complete live testing.
This supersedes the consent-pending state below. Serialized WSL2 checks used
candidate `7380f751`, the existing three managed Incus containers, protected
Linux-native evidence and the canonical reconcile/deployment commands. No new
fresh installation was run in this continuation.

Read-only native-host feasibility found Incus QEMU support and an available
Ubuntu 24.04 VM image, but approximately 19 GiB total WSL2 RAM. The canonical
node limits alone require 19 GiB and 8 CPU threads; the resource guard requires
these to fit inside the guest. A suitably sized guest plus its host cannot
fit the current memory ceiling. No overcommit, reduced-limit substitute,
container-as-native claim or native VM launch was attempted. A suitably sized
native target or increased host capacity remains required, not another live
permission grant.

## Local continuation: 2026-09-09

The user selected existing PR #293 for continued implementation/publication.
Branch `feature/cred-07-live-e2e-20260903` was clean at `8915cf38` before
changes; it is the only registered worktree. The active workflow file belongs
to issue #252 and is not executed or expanded by this issue-specific repair.
Local scope covers CRED-07-REQ-007/013/014: the two Classic browser evidence
writers, their storage regression tests, secure-path documentation and issue
evidence. Work is serialized in this task branch, with a read-only independent
reviewer. Required gates are focused browser tests, full local quality and
diff checks. No architecture/ADR boundary or infrastructure configuration is
changed. Native-Linux target, live consent and factual rotation reference
remain pending user input; no live command is authorized by this preflight.

## Initial read-only state

The preparation preflight on 2026-09-03 classified the checkout as WSL2 under
`/mnt/d`:

```text
kernel=Linux DESKTOP-AD2FST4 6.18.33.2-microsoft-standard-WSL2
python=Python 3.14.4
wsl_signal=microsoft-kernel
mnt_d=present
systemd_runtime=present
incus_binary=present
docker_binary=present
native_linux_evidence_root=absent
```

No native-Linux host or VM was discoverable from the workspace. Incus-managed
containers are the target nodes for the WSL2 run; they are not evidence of a
native-Linux host class.

Before operator consent, the states were `LIVE_CONSENT_MISSING` for WSL2 and
`LIVE_PREREQUISITE_MISSING` for native Linux. No mutating command was run in
that stage.

## Authorized WSL2 execution

The user subsequently granted explicit approval for mutating live execution.
The canonical installer was run headlessly with
`--confirm-reset --non-interactive-live-approval --allow-wsl-windows-filesystem`
against the `service-access` profile. The source checkout remained under
`/mnt/d`; installer and setup evidence were directed to the WSL-native root
`/home/micro/.local/state/tiny-swarm-world/evidence/`.

The final run is:

```text
run_id=20260903T072101Z
commit=be68f7e0
host_runtime_type=wsl2
reset_exit=0
setup_exit=0
live_approval_source=explicit_automation_flag
credential_sources=default catalog labels only
evidence=/home/micro/.local/state/tiny-swarm-world/evidence/cred07-wsl2-secure-20260903/wsl2/20260903T072101Z
```

The protected root, host directory and run directory were each verified as
user-owned mode `0700`. The run completed the platform, cluster, artifact,
secret, deployment and verification phases. No raw credential material was
recorded.

## Earlier bounded live failures and repairs

The following redacted runs are retained as diagnostic history, not as passes:

| Run | State | Stopped at | Result |
|---|---|---|---|
| `20260903T052421Z` | `LIVE_FAILED_AFTER_MUTATION` | Portainer bootstrap | Current Portainer rejected the legacy admin-init path with HTTP 403; deploy-time admin secret provisioning was added. |
| `20260903T054233Z` | `LIVE_BLOCKED_BEFORE_MUTATION` | reset confirmation | Direct fresh install was correctly refused without `--confirm-reset`. |
| `20260903T054250Z` | `LIVE_FAILED_AFTER_MUTATION` | managed-config inventory | `password_source` metadata was incorrectly classified as a secret-like assignment; scanner false-positive handling was added. |
| `20260903T061319Z` | `LIVE_FAILED_AFTER_MUTATION` | SonarQube admin access | SonarQube required a lowercase and special character; the catalog value and constraint were corrected. |
| `20260903T064605Z` | `LIVE_VERIFIED` for installer behavior | superseded evidence location | WSL2 setup was green, but the outer installer evidence still used the checkout path; the protected-root fix was then added. |

Only `20260903T072101Z` is the final protected-evidence candidate.

## Remaining preflight state

- WSL2 live prerequisite and consent: satisfied and observed.
- Native-Linux live prerequisite: `LIVE_PREREQUISITE_MISSING`; no target was
  supplied or discoverable.
- Protected custom/Infisical override: not run; no operator-owned `0600`
  credential file or non-secret credential-rotation reference was supplied.
- Browser acceptance runner: not run because its protected override/rotation
  contract is not satisfied. The installer and service/API acceptance remain
  separate from browser evidence.
