# RC1-R05 Test Results

- Runner and CI workflow contract tests: **passed**.
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
- No owned target qualification, protected-environment dispatch, full
  lifecycle run or failure drill was executed.
