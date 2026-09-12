# RC1-R01 Changed Files

Implementation:

- `src/tiny_swarm_world/domain/update/`
- `src/tiny_swarm_world/application/ports/update/`
- `src/tiny_swarm_world/application/services/platform/workflow/update.py`
- `src/tiny_swarm_world/infrastructure/adapters/update/`
- `src/tiny_swarm_world/infrastructure/composition.py`
- `src/tiny_swarm_world/infrastructure/composition_deployment.py`
- `src/tiny_swarm_world/infrastructure/composition_runtime.py`
- `src/tiny_swarm_world/infrastructure/composition_setup.py`
- `src/tiny_swarm_world/__main__.py`

Contract and operator surface:

- `documentation/arc42/09_decisions/adr-classic-update-contract.adoc`
- `documentation/user_guide/usage.adoc`
- `documentation/user_guide/installation.adoc`
- `tools/live/run_classic_acceptance.py`
- `.github/workflows/nightly-classic-live.yml`

Verification:

- `tests/domain/update/test_classic_update.py`
- `tests/application/services/platform/test_classic_update_workflow.py`
- `tests/infrastructure/adapters/update/test_json_state_store.py`
- `tests/test_classic_update_cli.py`
- `tests/test_ci_workflow_contract.py`
- `tests/application/services/platform/test_platform_workflows.py`
