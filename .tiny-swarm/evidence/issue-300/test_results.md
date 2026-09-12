# RC1-R04 Test Results

- Focused TLS suite: 15 tests passed, including reuse, permission, symlink,
  trust-drift and CA/bundle byte equality checks.
- Ruff lint and git diff --check: passed.
- Baseline main quality run 34720675824: 2,004 tests, 19 skipped; passed.
- Baseline compatibility run 34720675775: Python 3.12 and 3.13 passed.
- Baseline Sonar run 34720818090: EXTERNAL_GATE_FAILED, new security rating E.
- Repair full quality: PASS on Python 3.12.14, including both architecture gates,
  lint, mypy (668 source files) and 2,004 tests (18 skipped). Executed at
  `320f11f8722cb26fa289326178cae8a6486df1b5`; product, test, tool, workflow,
  configuration and dependency trees match this repair branch exactly.
- Repair hosted checks and exact-candidate scan: pending.

Historical evidence is preserved by Git history. Local tests do not qualify
live, browser or external acceptance.
