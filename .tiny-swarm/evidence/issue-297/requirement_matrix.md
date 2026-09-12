# RC1-R01 Requirement Matrix

Issue: #297 — Implement and verify the canonical Classic update workflow
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/297
Branch: `feature/rc1-r01-update-20260912`

| ID | Requirement | Type | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|---|
| R01-01 | Define update versus reconcile and select one safe reversible update scenario. | architecture / governance | `documentation/arc42/09_decisions/adr-classic-update-contract.adoc` | Three-Amigos decision; focused contract tests | VERIFIED_LOCAL |
| R01-02 | Provide one canonical update command with help and argument validation. | functional | CLI `platform update` | CLI help and invalid-argument tests | VERIFIED_LOCAL |
| R01-03 | Require live consent for a mutating update and report refusal clearly. | security / resilience | Existing CLI consent guard applied to update | CLI consent tests; refusal smoke check | VERIFIED_LOCAL |
| R01-04 | Preview and validate the intended transition before mutation. | functional | Update plan and preflight validation | Preview and blocked-transition tests; preview smoke check | VERIFIED_LOCAL |
| R01-05 | Reject unsupported transitions without downstream mutation. | resilience | Update transition validator | Unsupported-transition tests | VERIFIED_LOCAL |
| R01-06 | Define executable backup/state protection and rollback/recovery behavior. | resilience | Private JSON state store, rollback plan and `platform update --recover` | State-store, workflow recovery and CLI tests | VERIFIED_LOCAL |
| R01-07 | Apply and verify a supported change on healthy WSL2 and native Linux. | live | Existing deployment ports consumed by update workflow | Authorized host runs pending | BLOCKED |
| R01-08 | Preserve identities, persistent data, unrelated configuration and effective credentials. | resilience / security | Update scope limited to selected stack/image; no reset/bootstrap path | Composition and workflow tests; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-09 | Make repeated updates idempotent and recover interrupted updates safely. | resilience | Source-image guard, persisted last transition and reversible recovery | Repeat/failure/recovery tests; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-10 | Run post-update service/browser/API acceptance on both hosts. | live | Canonical runner phase contract | Authorized WSL2/native runs pending | BLOCKED |
| R01-11 | Consume the same command from host lifecycle packages and Classic Nightly. | integration | `tools/live/run_classic_acceptance.py`, `.github/workflows/nightly-classic-live.yml` | Static command consistency test; runner execution pending | VERIFIED_LOCAL_PENDING_LIVE |
| R01-12 | Complete regression, documentation and redacted live evidence. | quality / documentation | Issue evidence package and operator guide | Full local quality gate; live evidence pending | VERIFIED_LOCAL_PENDING_LIVE |

Live verification is intentionally not claimed by this branch. The repository
policy requires explicit operator consent and a qualified target for mutation.
