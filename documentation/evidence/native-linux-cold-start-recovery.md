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

## Native continuation on 2026-09-11 — initial findings

The published candidate was checked out on the native target. The first host
reboot recovered the three kernel controls, Swarm nodes and service replicas;
the canonical post-install module passed 37 tests (eight live, 29 static),
with no skips, both before and after selecting the candidate. The candidate
host prerequisite guard verified the native host; 139 focused regression
tests also passed in its existing Python 3.14 environment. This runtime does
not change the project's declared Python support contract.

A second distinct host boot again recovered the kernel controls and Swarm
control plane. However, protected run `20260911T191941Z` failed four tests
covering service/HTTPS routes and Pulsar/API/Manager authentication. The
120-second readiness window expired with Pulsar API and Pulsar Manager pending.
A later run, `20260911T192339Z`, passed Pulsar API authentication but still
failed three of 37 tests: service routes, HTTPS routes and Pulsar Manager login.
Reaching desired replica counts therefore did not establish service acceptance.

The volume comparison also found a Jenkins persistence defect: the stack mounts
`jenkins_home` at `/var/lib/jenkins`, while the running image uses
`JENKINS_HOME=/var/jenkins_home`. The actual home uses an anonymous volume whose
identity changed between observations around the second reboot. Equal volume
counts do not prove preserved data, and this observation alone cannot identify
specific lost records. Live correction requires selecting and backing up the
authoritative Jenkins data, controlling writes, and defining migration and
rollback before switching the home mount. At that stage, no live data migration or remount
had yet been attempted.

At that point runtime acceptance remained incomplete. The original bridge-prerequisite
failure is no longer observed in the bounded current-boot journal checks, but
Pulsar acceptance and Jenkins data persistence are separate open findings.
Detailed local evidence: `.tiny-swarm/evidence/native-cold-start-recovery/`.

## Bounded repair after continued operator authorization

Pulsar Manager responded on both internal ports (9527 and 7750), while its
host-published port failed. A protected archive of its existing named database
volume was verified, then only the manager task was recreated. The published
port recovered. This establishes recovery of the observed network path; it
does not prove a specific Docker internal defect or automatic cold-boot recovery.

Jenkins authenticated with the existing credentials and had no jobs or active
executors. The active home was selected as source; the old named destination
was empty. After quiet mode, a 1.2-second pause allowed consistent verified
archives and a copy of all 1276 entries. File bytes, ownership, permissions
and symlinks matched. The anonymous source is retained by a stopped keeper
container, and root-only archives and prior specifications remain on the node.
The targeted service mount now uses `jenkins_jenkins_home` at
`/var/jenkins_home`, matching the corrected compose configuration.

Post-repair protected run `20260911T194856Z` passed 37/37 (eight live, 29
static), with zero skips, and Jenkins authenticated successfully. Previous
failed runs remain historical evidence. This is manual repair acceptance; it
does not turn the earlier unaided cold-boot failure into success or recover
historical Jenkins data whose contents were never captured. Credential
rotation/session invalidation remain separate open CRED-09 requirements.

See [Jenkins home migration](../user_guide/jenkins-home-migration.md) for the
preconditions, verification and explicit source-volume rollback.

A further controlled Jenkins task replacement retained the same named home
and a harmless persistence probe. Both existing key files compared equal in
memory to the retained source; no key values or fingerprints were emitted.
The probe was removed after verification. Local full quality passed: policy,
lint, three architecture import contracts, 18 architecture tests, typecheck
and 1924 tests (18 skips).

## Full native host reboot after repair

The explicitly requested full VM reboot on 2026-09-11 completed without manual
post-boot repair. The host boot ID changed, all three kernel controls remained
active, all Incus/Swarm nodes recovered, and the canonical protected suite
passed 37/37 with zero skips in run `20260911T202411Z`. Its eight live checks
covered the configured HTTP/API/TLS and authentication contracts.

Jenkins retained the same named home, a harmless preboot probe and both
existing key files; authentication succeeded. The probe was removed afterward.
No deployment or forced task recreation was used to obtain this result.
This verifies this observed whole-host reboot, not power-loss recovery or
every future boot. Previous failed runs and historical-data/credential-rotation
limits remain part of the evidence record.

Service readiness in the post-repair host-reboot run completed in 53.264
seconds against the 120-second deadline, with no pending services.
