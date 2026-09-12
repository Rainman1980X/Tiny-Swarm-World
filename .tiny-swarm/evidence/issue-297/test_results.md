# RC1-R01 Test Results

Local verification completed on branch
`feature/rc1-r01-update-20260912`:

- focused update, CLI, CI-contract and platform taxonomy tests: **56 passed**;
- infrastructure composition regression tests: **102 passed**;
- `python3 tools/quality_gate.py quality`: **PASS**;
- full quality gate test phase: **1,982 passed, 18 skipped**;
- `git diff --check`: **PASS**;
- CLI preview smoke check: **completed without mutation**;
- CLI apply without `--live`: **refused with `REFUSED_LIVE_CONSENT_MISSING`**;
- recovery without stored state: **blocked without mutation**.

The earlier repository-wide `compileall` probe could not write existing
permission-protected cache files under `src/.../__pycache__`; it was not used
as the quality authority. The source quality gates above passed.

Live host, browser/API and external Sonar checks remain separate evidence
requirements and are not implied by local checks.
