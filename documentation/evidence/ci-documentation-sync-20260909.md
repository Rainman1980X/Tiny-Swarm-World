# Documentation CI repair: 2026-09-09

Baseline: `346641f8`, after externally merged PRs #293, #303 and #304.
PR #304's checks exposed two inherited #303 documentation regressions:
the README omitted the required live-operation surface catalog link, and its
governing SHA-256 cache no longer matched the rewritten README.

The repair restores that link and updates only the README hash in the skill
registry. No tests, runtime behavior, thresholds or architecture rules change.
An independent read-only reviewer verified the link, hash and minimal diff.

Verification:

- `PYTHONPATH=src python3 -m unittest tests.architecture.test_legacy_surface_documentation tests.architecture.test_skill_registry_integrity`:
  PASS, 16 tests.
- The first full gate under a Linux-native temporary checkout failed one
  existing legacy test that requires a Windows-translatable checkout path.
  The isolated checkout was moved to `/mnt/d`; the test then passed without
  changing or disabling it.
- `python3 tools/quality_gate.py quality`: PASS on the final repair content,
  including policy, lint, import contracts, 18 architecture tests, typecheck
  and 1913 tests in 143.654s with 18 opt-in skips.
- `git diff --check`: PASS. The registry's README hash matches the repaired
  file exactly; no other registry data changed.

This repairs publication quality. It does not establish native-Linux live
acceptance. Issue #285 was externally closed and its PRs were merged, but the
independent CRED-07 assessment retains the unexecuted native-Linux requirements
and the bounded matching operator/Vault override scope recorded under
`.tiny-swarm/evidence/issue-285/`.
