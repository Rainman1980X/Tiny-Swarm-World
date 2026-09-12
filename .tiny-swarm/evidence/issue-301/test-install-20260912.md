# RC1-R05 Test Installation Result

Date: 2026-09-12

This was an explicitly confirmed test-only installation using the local
`internal-test` credential catalog and the operator-selected Infisical test
identity. No production or protected RC1-live claim is attached to this run.

## Result

- The confirmed managed-node reset completed for all three Tiny Swarm World
  Incus nodes with zero apply or verification failures.
- The fresh setup passed preflight, host preparation, platform, Swarm,
  exposure, deployment bootstrap and artifact preparation/verification.
- Deployment apply stopped at `deployment:infisical-sync` with the redacted
  failure class `SecretManagementBlocker`.
- The orchestrator was stopped after the terminal failure and the managed
  test environment was reset again. No half-configured test cluster remains.

Status: `TEST_INSTALL_FAILED_SECRET_SYNC`

The failure does not establish RC1 live evidence. A future test installation
needs a Three-Amigos review of the Infisical sync state and an explicitly
approved strategy for any persistent Infisical data reset.
