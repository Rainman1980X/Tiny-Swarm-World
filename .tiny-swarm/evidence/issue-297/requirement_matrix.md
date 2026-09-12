# RC1-R01 Requirement Matrix

Issue: #297 — Implement and verify the canonical Classic update workflow
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/297
Parent: #294; native/WSL consumers: #298/#299; Nightly: #301; final audit: #302.
Repair publication branch: `fix/rc1-r01-pr-20260913`
Base: `1bac487e6ca1e86b1df6d813ed58037b1cbe253a` (`origin/main`).

Status: `INCOMPLETE`. The existing requirement IDs below remain authoritative.
This publication assembles only the four explicitly selected R01 commits;
current-branch scoped verification passed. Historical local results do
not establish live acceptance or close #297/#294. GitHub currently reports
#297 closed; that administrative state is not evidence of completed R01 gates.

## Repair findings mapped before assembly

| ID | Requirement / owning rows | Source evidence to assemble | Verification | Status |
|---|---|---|---|---|
| R01-F01 | Qualify actual runtime source and active task image/state convergence (R01-04/05/07/09). | `ca71a3d6` runtime port, adapter and workflow | Source review; runtime/workflow/adapter regressions | VERIFIED_LOCAL |
| R01-F02 | Preserve original recovery metadata, including repeated recovery after completed rollback (R01-06/09). | `ca71a3d6`, `a6baac14` | Repeat recovery and forward-failure regressions | VERIFIED_LOCAL |
| R01-F03 | Reject corrupt state fields and unknown task states before mutation or history filtering (R01-05/06/09). | `a6baac14` | Strict schema and malformed observation regressions | VERIFIED_LOCAL |
| R01-F04 | Require complete authenticated runner evidence and truthful failure propagation (R01-10/11/12). | `7083e1f7` | Canonical runner and authenticated acceptance runner tests | VERIFIED_LOCAL |
| R01-F05 | Explain static preview, observed apply, metadata limits and explicit configuration intent (R01-01/06/12). | `524e7c4f` | Source/text consistency and CLI regressions | VERIFIED_LOCAL |

## Original acceptance requirements

| ID | Requirement | Type | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|---|
| R01-01 | Define update versus reconcile and select one safe reversible update scenario. | architecture / governance | `documentation/arc42/09_decisions/adr-classic-update-contract.adoc` | Three-Amigos decision; focused contract tests | VERIFIED_LOCAL |
| R01-02 | Provide one canonical update command with help and argument validation. | functional | CLI `platform update` | CLI help and invalid-argument tests | VERIFIED_LOCAL |
| R01-03 | Require live consent for a mutating update and report refusal clearly. | security / resilience | Existing CLI consent guard applied to update | CLI consent tests; refusal smoke check | VERIFIED_LOCAL |
| R01-04 | Preview and validate the intended transition before mutation. | functional | Update plan and preflight validation | Preview and blocked-transition tests; preview smoke check | VERIFIED_LOCAL |
| R01-05 | Reject unsupported transitions without downstream mutation. | resilience | Update transition validator | Unsupported-transition tests | VERIFIED_LOCAL |
| R01-06 | Define executable backup/state protection and rollback/recovery behavior. | resilience | Private JSON state store, rollback plan and `platform update --recover` | State-store, workflow recovery and CLI tests | VERIFIED_LOCAL |
| R01-07 | Apply and verify a supported change on healthy WSL2 and native Linux. | live | Existing deployment ports consumed by update workflow | First WSL update/continuity passed at `a2ff63fe`; complete WSL/native scenarios pending | OPEN |
| R01-08 | Preserve identities, persistent data, unrelated configuration and effective credentials. | resilience / security | Update scope limited to selected stack/image; no reset/bootstrap path | Composition and workflow tests; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-09 | Make repeated updates idempotent and recover interrupted updates safely. | resilience | Observed source/target convergence, preserved original transition and recovery | Repeat/failure/recovery tests; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-10 | Run post-update service/browser/API acceptance on both hosts. | live | Canonical runner phase contract | Authorized WSL2/native runs pending | BLOCKED |
| R01-11 | Consume the same command from host lifecycle packages and Classic Nightly. | integration | `tools/live/run_classic_acceptance.py`, `.github/workflows/nightly-classic-live.yml` | Static command consistency test; runner execution pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-12 | Complete regression, documentation and redacted live evidence. | quality / documentation | Issue evidence package and operator guide | Full local quality gate; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |

R01 is `INCOMPLETE`: first WSL update evidence is partial, not cross-host
acceptance. See `test_results.md` for inspected artifacts and pending gates.
Main owns further consented execution, final evidence and merge readiness.
