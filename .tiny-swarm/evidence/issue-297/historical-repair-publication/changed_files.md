# RC1-R01 Changed Files

Scope against `origin/main` base `1bac487e`: 20 product/test/operator files
from exactly four selected commits, plus the six issue evidence files below.
No execution-workflow, TLS or unrelated release changes enter this PR.

## Product, tests and operator guidance

- `documentation/arc42/09_decisions/adr-classic-update-contract.adoc`
- `documentation/user_guide/usage.adoc`
- `src/tiny_swarm_world/application/ports/update/__init__.py`
- `src/tiny_swarm_world/application/ports/update/port_update_runtime_observer.py`
- `src/tiny_swarm_world/application/services/platform/workflow/update.py`
- `src/tiny_swarm_world/domain/update/__init__.py`
- `src/tiny_swarm_world/domain/update/runtime_observation.py`
- `src/tiny_swarm_world/infrastructure/adapters/update/json_state_store.py`
- `src/tiny_swarm_world/infrastructure/adapters/update/lxc_runtime_observer.py`
- `src/tiny_swarm_world/infrastructure/composition_setup.py`
- `tests/application/services/platform/test_classic_update_workflow.py`
- `tests/domain/update/test_runtime_observation.py`
- `tests/e2e/classic/run_authenticated_acceptance_live.py`
- `tests/e2e/classic/test_authenticated_acceptance_runner.py`
- `tests/infrastructure/adapters/update/test_json_state_store.py`
- `tests/infrastructure/adapters/update/test_lxc_runtime_observer.py`
- `tests/infrastructure/test_composition.py`
- `tests/tools/test_classic_live_runner.py`
- `tests/tools/test_secure_runtime_paths.py`
- `tools/live/run_classic_acceptance.py`

## Current issue evidence

- `.tiny-swarm/evidence/issue-297/requirement_matrix.md`
- `.tiny-swarm/evidence/issue-297/implementation_summary.md`
- `.tiny-swarm/evidence/issue-297/changed_files.md`
- `.tiny-swarm/evidence/issue-297/test_results.md`
- `.tiny-swarm/evidence/issue-297/remaining_risks.md`
- `.tiny-swarm/evidence/issue-297/acceptance_checklist.md`

Existing `completion_audit.md` and `three-amigos.md` remain historical records.
This package records repair readiness and pending acceptance; it does not
convert the historical incomplete audit into a release pass.
