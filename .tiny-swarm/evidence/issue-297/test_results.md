# RC1-R01 Test Results

Date: 2026-09-13. Publication product tip:
`f92d6b28f37ef086f4bc657de8939e4e4222d3f0`.
Environment: Linux/WSL, Python 3.14.4. Local checks use mocked external systems.

## Executed scoped checks

```bash
PYTHONPATH=src python3 -m unittest \
  tests.domain.update.test_classic_update \
  tests.domain.update.test_runtime_observation \
  tests.application.services.platform.test_classic_update_workflow \
  tests.infrastructure.adapters.update.test_json_state_store \
  tests.infrastructure.adapters.update.test_lxc_runtime_observer \
  tests.test_classic_update_cli \
  tests.infrastructure.test_composition.TestComposition.test_update_builder_wires_observer_without_running_commands_for_preview \
  tests.tools.test_classic_live_runner \
  tests.tools.test_secure_runtime_paths \
  tests.e2e.classic.test_authenticated_acceptance_runner
```

Result: **PASS — 99 tests, zero skips**, exit 0. Coverage includes the three
original independent reproducers and broader recovery, malformed-field,
recognized/unknown task-state, runner-summary, authentication and evidence-path
regressions. These are local tests; live-test counts in synthetic runner
payloads are not actual live results.

| Check | Result |
|---|---|
| `python3 tools/quality_gate.py verification-policy` | PASS |
| `python3 tools/quality_gate.py lint` | PASS |
| `python3 tools/quality_gate.py arch-lint` | PASS |
| `python3 tools/quality_gate.py arch-tests` | PASS |
| `python3 tools/quality_gate.py typecheck` | PASS |
| `git diff --check` and final staged check | PASS |

## Full-gate authority and equivalence

The integration owner selected scoped publication checks using the execution
worktree as the product-equivalent full-quality baseline. A Git comparison
against `a2ff63fe6597fe41a1fcb4102b41efcea247602d` found no differences in
`src`, `tests`, `tools`, `infra`, `.github`, or dependency/build configuration.
The new branch therefore does not rerun the full suite solely for packaging
and evidence changes. Main's full Python 3.12.14 gate at that exact execution
SHA passed: **2,061 tests, 18 skips**, 674 typechecked files, 3 import contracts
and 18 architecture tests. The retained log
`tsw-rc1-final-runtime-quality-20260913.log` was inspected read-only; SHA-256:
`b3b6824d1a65301d0e74e8b2f026005a23234c448da5edca0f139e3b6e229799`.
This supports the verified identical product tree; published-head CI remains
an independently observed gate.

Historical isolated repair evidence at `a6baac14`: 66 targeted tests and the
three exact independent in-memory reproducers passed; full Python 3.14 quality
passed with 2,046 tests and 18 skips. Laplace independently reported 44 focused
tests plus the three reproducers passed and approved that exact repair for
integration. This is scoped historical evidence, not the combined PR gate.

## Partial WSL live evidence and pending gates

Main executed the first actual A-to-distinct-B WSL update at `a2ff63fe`.
Read-only inspection of retained evidence found:

| Artifact relative to main's retained RC1 evidence root | Observation | SHA-256 |
|---|---|---|
| `update-operations/update/operation.json` | Candidate `a2ff63fe`; completed/passed, exit 0, duration 19.908 seconds. | `6cb5ed1f8c331db3246223bb2a2d378a7004b6cf38fe0661850dd318f2d0e5aa` |
| `update-continuity/post-update.json` | Same candidate; `passed: true`; controlled B, running image `sha256:79bb176ad687dd14905e6429adfe99d78f449e8dc1158743ef9fbf5061195e06`. | `b366eaae5bc735b9d507952038a16b7c7c8d73c59de44552da670292582f5379` |

Continuity flags for service/node/cluster identity, home/storage, private home
configuration, job inventory and fixture configuration/artifact were true.
No credential values or private hashes are reproduced. The complete WSL
scenario is **`LIVE_PARTIAL`**: authenticated acceptance, repeat/recovery and
remaining required scenarios were not complete at this evidence snapshot.

Update/recovery, installation-related behavior, preservation and browser/API
acceptance on both hosts are `APPLICABLE_LIVE`; this publication task executed
none of them itself. Main must complete and record the exact
candidate SHA, host/profile, immutable before/after task images, scenario,
commands, timestamps, exit codes and canonical `LIVE_*` outcomes.

PR CI and Sonar are `APPLICABLE_EXTERNAL`. Results for the published head must
be observed after publication; pending or unavailable checks are not green.

Update during consolidation: the WSL post-update and post-recovery suites at
`a2ff63fe` both passed 25 live tests plus seven API checks with zero skips,
failures or errors. Repeat update reported `no_op`, retained the same task and
container, and preserved the original recovery metadata. Recovery restored
the original image and fixture data. Native update, interrupted-update proof
and hosted execution remain open; these observations do not close R01.
