# RC1-R05 Test Installation Result

Date: 2026-09-12
Candidate SHA: `53836bb4ae3f07e4c5693dfbebbc58ac59f031e1`

This was an explicitly confirmed test-only installation using the local
`internal-test` credential catalog and the operator-selected Infisical test
identity. No production or protected RC1-live claim is attached to this run.

## Result

- The confirmed managed-node reset completed for all three Tiny Swarm World
  Incus nodes with zero apply or verification failures.
- The fresh setup completed successfully with exit code 0 after preflight,
  host preparation, platform, Swarm, exposure, deployment bootstrap, artifact
  preparation/verification, deployment apply, deployment verification and
  platform verification.
- Infisical project/environment preparation and synchronization passed:
  22 entries checked, 19 synchronized, zero optional or required entries
  missing. The evidence records only source counts and redacted metadata.
- Runtime endpoint checks passed for Portainer, Traefik, Nexus, Jenkins,
  Pulsar, SonarQube, Swagger, Infisical and Service Access.
- The test environment remains available on the Incus provider for inspection;
  the native Linux Hyper-V VM remains stopped. No protected RC1-live claim is
  attached to this local test.

Status: `TEST_INSTALL_PASSED`

The earlier sync failure was caused by the direct CLI test environment missing
the three generated Traefik Docker-secret name references. Those references
were added to the protected local test configuration before the clean rerun.
