# Test Results: #285 / CRED-07

## Local verification

- `PYTHONPATH=src python3 -m unittest tests.test_install_script`: PASS, 20 tests.
- `python3 tools/quality_gate.py quality`: PASS, 1908 tests, 18 expected skips;
  verification policy, lint, architecture lint/tests, typecheck and full test
  stages passed.
- `git diff --check`: PASS.

## WSL2 live evidence

All commands below used explicit live approval and the `service-access` profile.
Credential values are intentionally omitted.

| Check | Result |
|---|---|
| Protected fresh install at `20260903T072101Z` | PASS; reset 0, setup 0 |
| WSL2 host and `/mnt/d` checkout | PASS; kernel classified WSL2 |
| Protected evidence root | PASS; user-owned `0700` root/host/run directories |
| Setup phases | PASS; preflight, platform, cluster, secrets, artifacts, deployment and verification completed |
| Catalog source metadata | PASS; required entries resolved as `default` labels |
| Service readiness | PASS; all expected services `1/1` except completed one-shot bootstrap task |
| Protected installer-output redaction | PASS; URLs/users shown, password values not printed |
| Protected evidence redaction scan | PASS; no raw credential/header pattern observed |
| Separate `platform reconcile` with in-process catalog defaults | PASS; exit 0, three nodes verified |
| Portainer forced restart and recovery | PASS; service `1/1`, status endpoint HTTP 200 |
| Deployment readiness verification | PASS; 9 deployment verification targets |
| Direct catalog-backed service authentication | PASS for Portainer, Infisical, Nexus, SonarQube, Pulsar and Pulsar Manager; Jenkins PARTIAL because HTTP 200 alone does not prove identity |

The protected run is stored outside the checkout at:
`/home/micro/.local/state/tiny-swarm-world/evidence/cred07-wsl2-secure-20260903/wsl2/20260903T072101Z`.

## Non-pass states

- Native Linux: `LIVE_PREREQUISITE_MISSING`; no target was available.
- Custom/Infisical override: not run; protected input and rotation reference
  were not supplied.
- Browser acceptance: not run; the protected browser-runner contract was not
  satisfied.
- Credential-drift comparison: not verified; reconcile passed but no
  before/after comparison was recorded.

The direct authentication trace is in `service_authentication.md`. Earlier
bounded failures are summarized in `preflight.md`; none is reported as a pass.

## Completion recheck: 2026-09-08

Candidate: `d474e2ebb907b846d25a922698304bf75fd35fed`, branch
`feature/cred-07-live-e2e-20260903`. Local runtime: WSL2, Python 3.14.4.
This local runtime result does not substitute for the supported Python 3.12
and 3.13 compatibility checks listed below.

- `python3 tools/quality_gate.py quality`: PASS, exit 0. Verification policy,
  lint, all three import contracts, 18 architecture tests, typecheck across
  646 files and the full suite passed. The suite ran 1908 tests in 139.157s
  with 18 skips; those skips are not live verification.
- `git diff --check origin/main...HEAD` and `git diff --check`: PASS.
- Read-only inspection confirmed that the recorded protected WSL2 root,
  host and run directories remain user-owned mode `0700`; both historical
  `reset-run.exit` and `setup-run.exit` contain `0`. This is artifact
  inspection, not a fresh live execution.
- `gh pr view 293 --json headRefOid,statusCheckRollup`: the head matched the
  candidate; Locked Python quality gate, Conda Python 3.12, Conda Python 3.13
  and SonarCloud Code Analysis all reported `SUCCESS`.
  [PR #293 checks](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/pull/293/checks)
  are external evidence for that SHA only.
- Independent `issue-completion-auditor` review: `BLOCKED`. Native-Linux,
  override, credential-drift and browser acceptance remain open. Additional
  requirements for protected browser evidence and conclusive post-restart /
  Jenkins authentication are recorded in `remaining_risks.md`.

No new live installation, reset, authentication, browser or reconcile command
was executed during this recheck. No PR merge or branch cleanup was performed.

## Browser storage repair verification: 2026-09-09

Candidate: the reviewed browser-storage repair based on `8915cf38`; this
record is committed together with that repair. Tests ran on the final Python
content; subsequent changes only synchronized evidence/documentation.

- `PYTHONPATH=src python3 -m unittest tests.e2e.classic.test_browser_evidence_paths tests.e2e.classic.test_browser_e2e_contract tests.e2e.classic.test_post_install_browser_live`:
  PASS, 60 tests, 8 opt-in live skips. An initial regression fixture used a
  directory directly under world-writable `/tmp` and correctly failed path
  qualification; the fixture was moved beneath its private temporary parent.
- `python3 tools/quality_gate.py quality`: PASS, exit 0. Policy, lint, three
  import contracts, 18 architecture tests, typecheck (647 files), and 1913
  tests passed in 138.101s, with 18 opt-in skips. No skip is live evidence.
- `git diff --check`: PASS.
- Independent read-only repair review: no blocking code defect; evidence
  synchronization findings were corrected. Completion remains `BLOCKED`.
- No live infrastructure, authentication, browser or lifecycle check executed.
  External checks require the published repair SHA; old success is not reused.
