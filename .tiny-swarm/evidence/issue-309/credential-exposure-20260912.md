# RC1-R08 Credential Exposure Containment

Date: 2026-09-12

## Observation

A read-only Docker service inspection on the local Swarm manager returned a
Jenkins administrator environment value to the agent terminal. The value is
not repeated here and was not copied into a file, issue, PR, log or evidence
artifact.

## Three-Amigos decision

The requirement, architecture and security reviewers classify the value as
compromised and require rotation or revocation before another protected live
run. Replacing only the Swarm environment entry is insufficient because the
existing Jenkins account state is persistent and the repository does not
provide a safe, generic rotation operation for this account.

## Containment

- No further mutating live command was executed after the observation.
- The protected live workflow remains fail-closed.
- The native Hyper-V test VM was shut down because it is not needed by the
  WSL2 runner or its Incus target cluster.
- The value is absent from repository changes and committed evidence.

## Required operator action

Use the approved operator secret source to rotate or revoke the Jenkins
administrator credential, then supply only the non-secret change reference to
the protected live workflow. The repository must not invent a replacement
credential or accept a credential pasted into a command line.

Status: `LIVE_BLOCKED_BEFORE_MUTATION` pending operator-owned rotation and
secure WSL-native environment-file provisioning.
