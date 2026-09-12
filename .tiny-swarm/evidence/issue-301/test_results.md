# RC1-R05 Test Results

- Runner and CI workflow contract tests: **passed**.
- Full quality gate: **passed**, 2,004 tests, 18 expected skips.
- Disposable test-profile rotation bypass and redacted evidence-status tests:
  **passed**.
- Python syntax compilation for the runner: **passed**.
- git diff --check: **passed**.
- Runner registration observation: **PASS**, `tsw-protected-wsl2` online with
  `self-hosted`, `Linux`, `X64`, `tsw-protected`, `classic-live` and
  `tsw-classic` labels.
- Local runner capability observation: **PASS**, Incus 6.0.5 and Docker 29.8.0
  available on Linux/x64 with Python 3.14.
- Approved workflow-dispatch guard drill: **FAIL_CLOSED**, [run
  34692542906](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34692542906)
  reached the runner and stopped before mutation because all required
  repository live variables were empty.
- Earlier disposable test-profile dispatches: **FAIL_PRECHECK**, [run
  34717383985](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34717383985)
  reached the runner, accepted the secure env file and test-only profile, then
  stopped in setup preflight. Redacted evidence records
  `reason=phase 'preflight' returned failed` and the failed phase list; no
  credential or raw command output was persisted.
- Earlier retries [34711696044](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34711696044),
  [34711835973](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34711835973)
  and [34716893130](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34716893130)
  failed in the same hosted setup path while the runner wrapper was being
  hardened. The queued diagnostic retry [34717461463](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34717461463)
  was cancelled before execution.
- Clean local test-only installation: **PASS**, candidate SHA
  `53836bb4ae3f07e4c5693dfbebbc58ac59f031e1`, Incus/LXC provider, exit code 0.
  The run passed all setup phases, Infisical synchronization and endpoint
  verification; redacted evidence is recorded in `test-install-20260912.md`.
- The disposable workflow no longer reads
  `TSW_CLASSIC_CREDENTIAL_ROTATION_REFERENCE`; the remaining GitHub variables
  and runner-local 0600 env file are still prerequisites.
- Final hosted lifecycle: **PASS**, [run
  34719043422](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34719043422)
  finished `LIVE_VERIFIED` on commit
  `9d0082ebcb86cf18e81be76aeec00c613c7ceebd`. Setup completed all 18 phases;
  platform verification, Reconcile, Update and Recovery each passed; all four
  acceptance operations passed with 37 tests and zero skips. The uploaded
  artifact contains the redacted `run-summary.json` and checksums.
- A controlled required-scenario failure drill has not yet been executed, so
  that acceptance item remains open.
