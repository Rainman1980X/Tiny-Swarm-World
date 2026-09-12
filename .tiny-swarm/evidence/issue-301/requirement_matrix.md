# RC1-R05 Requirement Matrix

Issue: #301 — Run the complete Classic lifecycle on a qualified protected self-hosted runner
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/301
Branch: feature/rc1-r05-runner-qualification-20260912

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R05-01 | Diagnose runner availability, labels, ownership and capabilities. | Nightly qualification and runner-qualification-20260912.md | Runner registration, labels and local Incus/Docker capability observed; target ownership pending | VERIFIED_RUNNER_PENDING_TARGET |
| R05-02 | Use protected environment, scoped credentials, consent and concurrency. | Workflow environment, ownership/secret checks and non-canceling concurrency | Workflow contract tests | VERIFIED_LOCAL |
| R05-03 | Keep orchestration in the canonical thin runner. | Nightly invokes run_classic_acceptance.py | Workflow contract test | VERIFIED_LOCAL |
| R05-04 | Execute Fresh, acceptance, Reconcile, Update, acceptance and Recovery. | RC1-R03 runner phase chain | Phase order test; live execution pending | VERIFIED_LOCAL_PENDING_LIVE |
| R05-05 | Run against isolated target and retain diagnostics on failure. | Runner redacted terminal evidence and fail-stop loop | Local runner contract; target run pending | VERIFIED_LOCAL_PENDING_LIVE |
| R05-06 | Produce a real successful final-candidate run. | Workflow remains configured for protected runner | No successful run available | BLOCKED_LIVE |
| R05-07 | Evidence records SHA, runner, scenarios, durations and artifacts. | Payload now records safe runner identity/label and phase timings | Static inspection; real artifact pending | VERIFIED_LOCAL_PENDING_LIVE |
| R05-08 | Required failures propagate non-green; no skipped success. | Runner exit status and workflow job dependency | Existing tests; live failure drill pending | VERIFIED_LOCAL |
| R05-09 | Scheduled and manual dispatch behavior is validated. | Existing schedule/dispatch inputs and approval guard | Approved manual dispatch reached runner and failed closed on missing prerequisites | VERIFIED_DISPATCH_GUARD_PENDING_LIVE |
| R05-10 | Link successful run and evidence into RC1. | Release evidence consumer path defined | Successful run pending | BLOCKED_LIVE |

The issue remains open because the protected environment, owned target and
full self-hosted execution have not yet been supplied or observed.
