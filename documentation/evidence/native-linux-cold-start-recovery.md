# Native Linux bridge recovery

## Confirmed failure and correction

The observed native Linux host had `br_netfiltern` in its operator-owned
modules-load configuration. During boot systemd could not find that module.
Docker then failed to restore `docker_gwbridge` because
`net.bridge.bridge-nf-call-iptables` was missing. Network inspection still
returned the persisted network object; this did not prove that the bridge
driver had restored it.

Correcting the module entry to `br_netfilter`, loading it, activating the three
documented kernel controls and restarting Docker restored the running service
replicas. No network, Swarm state, volume or credential was deleted. The original
module file was backed up on the operator host before replacement.

## Ownership and prerequisite guard

Kernel persistence remains operator-owned. Reviewed templates live in
`infra/config/host/`; installation instructions explain how to apply them and
restore prior configuration. Native deployment bootstrap/apply now consumes
`PortHostPreparation.verify()` before preparation, secret creation, stack
mutation or HTTP readiness waiting. Missing, disabled, unreadable or unverified
kernel state blocks deployment with `host_kernel_prerequisites_missing`.

The guard verifies present prerequisites, not Docker's complete network state.
WSL retains its existing host preparation path. Service readiness remains a
separate verification step. Neither node Ready nor replica counts establish
credential validity or persisted application-data integrity.

## Verification scope

Regression tests cover prerequisite failure before mutations, verification
exceptions, successful continuation and native/WSL composition selection.
Runtime acceptance requires kernel controls active after host reboot, no new
bridge restoration error, service convergence and protected authenticated
acceptance. Two reboot cycles are the intended persistence check; record each
executed result in the runtime evidence package. Do not infer reboot success
from the initially recovered service replicas.

The original full local quality run found an unrelated skill-registry cache
mismatch. The two stale cache entries were synchronized with the existing
file bytes without changing the integrity test. The subsequent
`python3 tools/quality_gate.py quality` run passed: policy, lint, three import
contracts, 18 architecture tests, typecheck (649 files), and the full suite
(1924 tests, 18 skipped). This local result does not complete native live
acceptance or prove reboot persistence.
