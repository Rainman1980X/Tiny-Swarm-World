# Verification results

Local focused: 56 tests passed via
`PYTHONPATH=src python3 -m unittest tests.e2e.classic.test_authenticated_acceptance_runner tests.e2e.classic.test_authenticated_service_contract tests.e2e.classic.test_browser_e2e_contract`.

First full gate reached typecheck and failed a tuple annotation in a new mock
fixture. Corrected without weakening tests. Pre-SPA-fix `python3 tools/quality_gate.py quality`
passed all six stages, exit 0: 1972 tests (18 skipped), 18 architecture tests,
three import contracts, lint, verification policy and typecheck across 655 files.
Skipped local tests are not live execution. `git diff --check` passed.

Diagnostic WSL2 runs discovered and repaired Nexus modal interaction, distinct
Portainer/Infisical/Pulsar Manager rejection messages, and explicit Portainer
HTTP 422 rejection schema. Diagnostic reports retain dirty_checkout=true and
LIVE_PARTIAL; they do not establish final-candidate success.

Native existing VM reachable and trusted key verified; isolated Selenium
installation and actual headless Firefox startup succeeded. Final service and
restart acceptance below supersedes this prerequisite-only observation.

## Three Amigos loop 2 — SPA DOM replacement

Candidate `e5994d3aa9bc0a81bb3a47b56794425f37293743` native baseline
`20260912T082939927270Z`: all nine browser routes and seven protected API
checks passed, including invalid rejection; LIVE_VERIFIED for that candidate.
WSL baseline `20260912T082919110392Z`: Sonar browser returned
StaleElementReferenceException; all API probes passed. That run remains
LIVE_PARTIAL. The retained exception class does not establish the exact throw
site. Password-form observation had an uncovered stale-DOM failure path.

QA approved reacquiring DOM elements on bounded stale-only retries, with
exhaustion raising instead of implying absence. Credentials are not resubmitted.
Regressions cover stale-to-visible, stale-to-absent, exhaustion and unrelated
exception propagation. Focused browser contract: 27 tests PASS. Full local gate: all six stages PASS,
exit 0; 1974 tests (18 local skips), 18 architecture tests, three contracts and
655 typechecked files. Corrected-candidate reruns follow; no historical run is
relabeled.

## Final candidate acceptance — 2026-09-12

Actual clean tested code on both hosts: `d254b76980a344a67295d8395e61002bf0730b0c`.
[Machine-readable reports](live_results_20260912.json) retain twelve scenario and
component results, exact UTC times/durations, exits, route assertions, task IDs,
private artifact references/checksums and original failure states.

| Host | Phase | Started UTC | Duration | Exit | Result |
|---|---|---|---:|---:|---|
| wsl2 | baseline | 2026-09-12T08:35:49.691433+00:00 | 69.026 s | 0 | LIVE_VERIFIED |
| wsl2 | post-restart | 2026-09-12T08:47:51.483307+00:00 | 70.967 s | 0 | LIVE_VERIFIED |
| native_linux | baseline | 2026-09-12T08:35:59.710660+00:00 | 58.489 s | 0 | LIVE_VERIFIED |
| native_linux | post-restart | 2026-09-12T08:54:23.421662+00:00 | 59.624 s | 0 | LIVE_VERIFIED |

Each final phase executes nine actual headless Firefox route checks, including
six required UI logins with invalid rejection and a fresh valid browser session;
Pulsar admin API has navigation plus API authentication, not a UI login form.
Seven protected API checks each verify invalid rejection and authenticated access.
Eight canonical HTTP/API/TLS checks pass both before and after every phase.
No final live test is skipped. Readiness alone never establishes authentication.

### Executed command context

All runs execute from the clean repository root. WSL2 uses:

```bash
PYTHONPATH=src ~/.local/state/tiny-swarm-world/cred07-browser-venv/bin/python \
  -m tests.e2e.classic.run_authenticated_acceptance_live --approve-live --phase baseline
PYTHONPATH=src ~/.local/state/tiny-swarm-world/cred07-browser-venv/bin/python \
  -m tests.e2e.classic.run_authenticated_acceptance_live --approve-live --phase post-restart
```

Native Linux uses the existing Hyper-V VM, reached exclusively via Windows
PowerShell's OpenSSH with the previously trusted host-key alias. Its changing IP
is transport detail, not a second target. No passwords or connection strings are
published. Native invocation (same command for both recorded phase values):

```bash
PYTHONPATH=src:.venv/lib/python3.14/site-packages \
  ~/.local/state/tiny-swarm-world/cred08-browser-venv/bin/python \
  -m tests.e2e.classic.run_authenticated_acceptance_live --approve-live \
  --phase post-restart \
  --env-file ~/.local/state/tiny-swarm-world/native-live-installation.env
```

WSL kernel: `6.18.33.2-microsoft-standard-WSL2`; native kernel:
`7.0.0-31-generic`, Ubuntu 26.04.1. Native runtime Python 3.14 is an observed
host prerequisite, not a change to the project's Python 3.12 compatibility target.
Canonical source selection and protected storage are qualified before browser
construction. Private evidence directories are 0700 and reports 0600; screenshots,
traces, session cookies, tokens and raw service specifications are excluded.
Browser sessions are closed. Intended service ForceUpdate counters remain;
no volumes, credentials or settings were deleted and no rollback is needed.

### Three Amigos loop 3 — observed restart state and recovery

The approved restart boundary covers Infisical, Jenkins, Nexus, Portainer,
Pulsar, Pulsar Manager and SonarQube on the existing three-node environments.
Commands are `incus exec swarm-manager -- docker service update --force
--detach=true <service>`; exact service commands and before/after task IDs are
in the JSON. Jenkins persistent home was checked before mutation. No database,
whole VM, networking or provider reset is part of this acceptance.

WSL attempts at 08:37:21 and 08:40:18 UTC remain LIVE_FAILED_AFTER_MUTATION.
The first records CalledProcessError without its exact failing command; its
cause is unknown. The second records a nonzero Portainer update despite observed
replacement and subsequent healthy state. Original stderr was not retained;
it is classified as ambiguous external-command completion, not a proven cause.
A recovery authentication phase at 08:38:54 passed, but does not substitute for
the final all-service restart scenario. After the second attempt the remaining
Pulsar update returned exit 0; its exact invocation timestamp was not captured.
Its predecessor is taken from retained task history, explicitly not a pre-command
snapshot. The sequence is bounded by the failed attempt and the 08:44:55 recovery.
Reconciliation verified the five already-replaced services without another
mutation and restarted only Pulsar Manager and SonarQube. Its exit-0 report
correctly remains LIVE_PARTIAL until paired with fresh authentication. Its direct
spec comparison covers that recovery interval, not the first failed attempts.
A first final login run at 08:45:55 remained LIVE_PARTIAL because SonarQube's
canonical authenticated check was not ready. The later complete run passed.

Native restart at 08:45:54 recorded all seven commands exit 0 and all new tasks,
but its raw spec comparison failed. It remains LIVE_FAILED_AFTER_MUTATION.
Read-only inspection found Docker-materialized absent defaults and reordered
Portainer mounts. The reviewed recovery comparison fills only absent documented
update/restart/stop-grace defaults, preserves explicit values/nulls and unknown
fields, sorts complete mount mappings retaining duplicates, separately requires
ForceUpdate +1, and compares every other field exactly. All seven distinct
expected service rows pass on both hosts. The exact normalization schema is in
the spec-recovery reports; defaults reference the
[Docker service documentation](https://docs.docker.com/reference/cli/docker/service/create/).

PreviousSpec refers to each service's immediately preceding update, linked to
the recorded task replacement sequence; there were no intervening updates before
comparison or final native authentication. On WSL it proves the last update per
service, not retrospectively every earlier repeated update. Credential environment,
images and full mount mappings remain equal. The read-only spec component retains
LIVE_PARTIAL; combined with replacement and fresh final authentication it supports
the separate composite LIVE_VERIFIED result. No original failure is relabeled.
The initial native helper invocation lacked `.` on PYTHONPATH and exited 1 before
inspection; the corrected read-only invocation passed without a runtime mutation.

### External and publication boundary

At tested code candidate d254b769, GitHub Locked Python quality gate, Conda
Python 3.12/3.13 and SonarCloud Code Analysis all passed on PR #312.
Python run: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34683680294
Conda run: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34683680362
Final evidence publication changes documentation/JSON only. The live SHA remains
d254b769; any later executable change requires affected reruns. PR-head checks
are verified separately during publication. No merge or broader release approval
is inferred from these checks.

Independent final QA review reran the focused three-module command: 58 tests
passed, exit 0. All twelve manifest SHA-256 hashes matched protected source JSON;
`git diff --check` passed and no executable diff exists after d254b769.

For the final documentation/JSON-only commit, the full local gate is not repeated:
no executable/configuration/quality-policy file changed after the already passed
d254b769 gate. QUALITY.md's documentation gate (`git diff --check`) and independent
JSON/digest/evidence review apply. The earlier full gate is attributed only to its
tested code candidate; final PR CI is a separate publication check.
