# RC1-R05 Requirement Matrix

Issue: #301 — Run the complete Classic lifecycle on a qualified protected self-hosted runner
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/301
Branch: feature/rc1-r05-runner-qualification-20260912

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R05-01 | Diagnose runner availability, labels, ownership and capabilities. | Nightly qualification and runner-qualification-20260912.md | Hosted qualification passed on `tsw-protected-wsl2`; dispatch target owner `tsw-test-incus-local` accepted by the qualification guard | VERIFIED_HOSTED |
| R05-02 | Use protected environment, scoped credentials, consent and concurrency. | Workflow environment, ownership/secret checks and non-canceling concurrency | Workflow contract tests | VERIFIED_LOCAL |
| R05-03 | Keep orchestration in the canonical thin runner. | Nightly invokes run_classic_acceptance.py | Workflow contract test | VERIFIED_LOCAL |
| R05-04 | Execute Fresh, acceptance, Reconcile, Update, acceptance and Recovery. | RC1-R03 runner phase chain | Hosted run 34719043422: setup, platform verify, acceptance, reconcile, acceptance, update, acceptance, recovery and acceptance all passed | VERIFIED_HOSTED |
| R05-05 | Run against isolated target and retain diagnostics on failure. | Runner redacted terminal evidence and fail-stop loop | Hosted run used the owned `tsw-test-incus-local` target reference and uploaded redacted evidence; earlier failures retained redacted artifacts | VERIFIED_HOSTED |
| R05-06 | Produce a real successful final-candidate run. | Workflow remains configured for disposable test runner | [Hosted run 34719043422](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34719043422) finished `LIVE_VERIFIED` | VERIFIED_HOSTED |
| R05-07 | Evidence records SHA, runner, scenarios, durations and artifacts. | Payload now records safe runner identity/label and phase timings | Uploaded `run-summary.json` records SHA `9d0082ebcb86cf18e81be76aeec00c613c7ceebd`, runner, eight operations, durations and zero skipped tests | VERIFIED_HOSTED |
| R05-08 | Required failures propagate non-green; no skipped success. | Runner exit status and workflow job dependency | Hosted failure runs were non-green; successful run had exit code 0 for every operation and no skips. A controlled failure drill remains open | VERIFIED_HOSTED_PENDING_FAILURE_DRILL |
| R05-09 | Scheduled and manual dispatch behavior is validated. | Existing schedule/dispatch inputs and approval guard | Approved manual dispatch 34719043422 passed qualification and completed the full chain; blocked dispatch drill remains recorded | VERIFIED_HOSTED |
| R05-10 | Link successful run and evidence into RC1. | Release evidence consumer path defined | Successful run and artifact are linked in `test_results.md` and the RC1 decision row | VERIFIED_HOSTED |
| R05-11 | Disposable test execution must not require a credential-rotation reference. | Explicit test-only execution profile in the canonical runner and workflow | `test_disposable_test_profile_does_not_require_rotation_reference`; workflow contract test | VERIFIED_LOCAL |
| R05-12 | The test workflow must stop reading the rotation-reference GitHub variable while retaining consent, Linux, ownership, secure-file and update-input guards. | Nightly workflow test-only invocation and reduced variable contract | `test_classic_live_workflow_is_protected_and_fail_closed` | VERIFIED_LOCAL |
| R05-13 | Terminal evidence must identify the disposable test profile and record rotation as not applicable without writing a credential or reference value. | Redacted runner summary fields | `test_disposable_test_profile_does_not_require_rotation_reference`; static redaction contract | VERIFIED_LOCAL |
| R05-14 | Operator documentation must explain the remaining GitHub variables and the runner-local secure env file. | Updated secure live/test path guide | `git diff --check`; documentation inspection | VERIFIED_LOCAL |

The hosted lifecycle is verified. The issue remains open only for the
controlled required-scenario failure drill and its independent completion
audit.
