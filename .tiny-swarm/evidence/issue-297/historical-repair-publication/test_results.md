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

### Published runner PATH regression

Compatibility run 34723984143 failed the approved-runtime-path regression on
Python 3.12 and 3.13: a login shell replaced the supplied PATH. The operation
launcher now uses a non-login shell while retaining explicit protected-config
loading and evidence-path pinning. Thirty targeted runner/authentication/CI
contract tests pass locally. Required hosted checks must pass on the new head.
The existing real three-role review remains historical; further review uses
an explicit requirement/architecture/QA fallback because all callable agents
reported their usage limit.

### Observed update scope defect

The native update initially applied the selected Jenkins image and then failed
in `deployment:infisical-sync` because unrelated TLS secret references were
absent. The failed operation is retained; supplying the references allowed the
nominal cross-host update/recovery proofs to complete, but did not resolve the
scope defect. Composition now excludes global Infisical bootstrap/sync/seed
from image updates and only wires administrative access for selected stacks.
The new composition regression first failed on the Infisical client constructor,
then exposed an additional unrelated SonarQube step. Both causes are fixed;
all 104 composition tests pass under Python 3.12.14.

Requirement/architecture/QA fallback review: this preserves the documented
selected-stack boundary, leaves full setup wiring covered by existing tests,
and requires a native retest with the original protected environment lacking
those references. No secret defaults, credentials or test exceptions were added.
This is an explicit single-thread role review, not a new independent-agent
approval. The earlier independent update/recovery reviews remain historical.

Hosted run 34724253777 on `d59f42cf` passed all 14 operations, including four
authenticated phases (each 25 live tests plus seven API checks, zero skips).
It reused an existing target and therefore does not establish fresh-install
acceptance. The later scope fix requires current-head CI and live verification.

The complete local gate after this scope repair passed under Python 3.12.14:
2,062 tests, 18 explicit live/optional skips; lint, verification policy,
three import contracts, 18 architecture tests and 674 typechecked files passed.
Retained log: `tsw-rc1-r01-scope-quality.log`. This is local verification only.

### Post-apply observation boundary

At execution SHA `3b68ca95`, native update verification failed at
23:24:24.704 UTC; Docker reported the selected update completed at
23:24:24.602 UTC and subsequent inspection found the correct running B task.
The first summary does not retain its nested typed reason, so a changing
snapshot is an inference from timing and source inspection, not a proven
root-cause label for that historical attempt. Canonical recovery succeeded.

Source review and deterministic tests expose an immediate-failure path when
the same service changes between the observer's two inspections. A distinct
`UpdateObservationChanged` now permits only this read to repeat within the
existing post-apply attempt/time bound. Deployment is not repeated. Invalid
schema/task state, replaced identity, missing access and pre-apply instability
still fail closed; continuous changes exhaust the bound without success.
The successful result records the observation attempt count. Forty-one focused
workflow/adapter tests pass, including transient and exhausted observations.
This scoped requirement/architecture/QA fallback applies the resilience skill;
it does not claim a new independent-agent review.

The controlled WSL failing image at `3b68ca95` produced a nonzero update result,
then canonical recovery and repeated recovery succeeded. Jenkins identity,
configuration, credentials and fixture data were preserved. Post-recovery
acceptance passed 25 live tests plus seven API checks with zero skips.
Retained sequence: `scope-validation/20260912T232350Z.json`.

Full local quality after the typed observation repair: PASS under Python
3.12.14, 2,066 tests with 18 explicit live/optional skips, all architecture,
lint, policy and type checks passed. Log: `tsw-rc1-snapshot-quality.log`.
