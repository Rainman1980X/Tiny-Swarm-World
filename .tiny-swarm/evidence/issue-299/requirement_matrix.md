# RC1-R03 Requirement Matrix

Issue: #299 — Complete final-candidate WSL2 lifecycle, failure recovery and restart resilience
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/299
Branch: `feature/rc1-r03-wsl2-recovery-20260912`

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R03-01 | Define Fresh, Reconcile, Update, Recovery, failure and restart scenarios. | `scenario_matrix.md`; runner phase sequence | Runner contract test | VERIFIED_LOCAL |
| R03-02 | Qualify protected source/evidence storage and consent boundaries. | Existing secure path checks in `run_classic_acceptance.py` | Existing runner contract tests; target run pending | VERIFIED_LOCAL_PENDING_LIVE |
| R03-03 | Execute Fresh → acceptance → Reconcile → acceptance → Update → acceptance. | Canonical runner commands | Static order assertion; qualified WSL2 run pending | VERIFIED_LOCAL_PENDING_LIVE |
| R03-04 | Cover partial deployment and managed service recovery. | Recovery phase reuses persisted update state and stops on failed required phase | Mocked update recovery tests from R01; live fault injection pending | VERIFIED_LOCAL_PENDING_LIVE |
| R03-05 | Prove WSL2 restart restores identities, routes and readiness. | Scenario and evidence contract defined | Qualified WSL2 restart evidence pending | BLOCKED_LIVE |
| R03-06 | Verify authenticated operations after restart. | Repeated acceptance phase contract | Qualified WSL2 credential/browser/API run pending | BLOCKED_LIVE |
| R03-07 | Maintain redacted evidence with SHA, host, timing and recovery outcome. | Existing terminal evidence writer and runner phase labels | Local contract tests; real run pending | VERIFIED_LOCAL_PENDING_LIVE |
| R03-08 | Re-run dependent scenarios after fixes and distinguish live from local evidence. | Issue evidence and runner stop-on-failure behavior | Local quality gate; live candidate run pending | VERIFIED_LOCAL_PENDING_LIVE |

The issue remains open because no qualified WSL2 target or explicit live
execution authorization was available in this implementation session.
