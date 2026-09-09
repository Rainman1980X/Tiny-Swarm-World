# Changed Files: #285 / CRED-07

## Product and test changes

- `src/tiny_swarm_world/installer.py`
- `src/tiny_swarm_world/domain/configuration/internal_test_credentials.py`
- `src/tiny_swarm_world/application/services/deployment/secret_management.py`
- `src/tiny_swarm_world/infrastructure/adapters/clients/lxc/swarm/stack_prerequisite_registry.py`
- `src/tiny_swarm_world/infrastructure/adapters/clients/lxc_swarm_runtime.py`
- `src/tiny_swarm_world/infrastructure/composition_deployment.py`
- `infra/config/compose/portainer/docker-compose.yml`
- `tools/install_debugger.py`
- `tests/test_install_script.py`
- `tests/test_installer.py`
- `tests/test_install_debugger.py`
- `tests/domain/configuration/test_internal_test_credentials.py`
- `tests/application/services/deployment/test_secret_management.py`
- `tests/infrastructure/adapters/clients/test_lxc_swarm_runtime.py`
- `tests/infrastructure/adapters/repositories/test_compose_file_repository_yaml.py`

## Documentation and issue evidence

- `.tiny-swarm/evidence/issue-285/live_results_20260909.json`: redacted authorized WSL2 run results, hashes and native-resource blocker.

- `tests/e2e/classic/browser_e2e_contract.py`: protected live evidence routing.
- `tests/e2e/classic/test_post_install_browser_live.py`: protected run directories.
- `tests/e2e/classic/test_browser_evidence_paths.py`: storage regression coverage.
- `documentation/evidence/wsl2-secure-live-path.md`: shared browser storage contract.

- `documentation/arc42/08_configuration/internal-test-credential-catalog.md`
- `.tiny-swarm/evidence/issue-285/requirement_matrix.md`
- `.tiny-swarm/evidence/issue-285/preflight.md`
- `.tiny-swarm/evidence/issue-285/implementation_summary.md`
- `.tiny-swarm/evidence/issue-285/remaining_risks.md`
- `.tiny-swarm/evidence/issue-285/acceptance_checklist.md`
- `.tiny-swarm/evidence/issue-285/test_results.md`
- `.tiny-swarm/evidence/issue-285/completion_audit.md`
- `.tiny-swarm/evidence/issue-285/review.md`
- `.tiny-swarm/evidence/issue-285/changed_files.md`
- `.tiny-swarm/evidence/issue-285/service_authentication.md`

The raw live bundle is ignored and stored outside the checkout at the protected
WSL-native path documented in `test_results.md`; raw credentials are not part
of this branch or PR.
