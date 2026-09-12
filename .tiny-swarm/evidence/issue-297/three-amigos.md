# RC1-R01 Three-Amigos Decision

Date: 2026-09-12
Issue: #297
Decision: `PROCEED_WITH_ACCEPTED_ASSUMPTIONS`

## Requirement Lead

The canonical transition is an update of one existing service stack from its
currently resolved image reference to an explicitly supplied target image
reference. Reconcile remains the operation that converges the existing desired
configuration. Update owns the explicit source/target transition, preview,
backup metadata, apply and recovery result.

The first supported scenario is a single stack image update. It is reversible
by supplying the recorded source image as the target in a recovery run. The
command must not reset nodes, delete persistent volumes, change credentials or
modify unrelated stacks.

## System Architect

The command is an application workflow composed in
`infrastructure/composition.py` and backed by existing deployment ports. No
new orchestration engine, provider, runtime or service boundary is introduced.
The domain update plan contains only validated value data and has no shell,
filesystem, Docker or YAML dependencies.

## Python Automation Developer

The CLI validates the transition before constructing mutating services. The
application workflow receives an update plan and uses the existing stack
deployment gateway. Infrastructure owns image resolution, state persistence
and command details. Failures remain typed workflow outcomes and are safe to
serialize.

## Test / Evidence Reviewer

Local tests cover command parsing, preview, unsupported transitions, consent,
idempotence and failure propagation with mocked ports. Live update, browser/API
acceptance and cross-host preservation are `APPLICABLE_LIVE`; they remain
unverified until explicit consent and qualified WSL2/native-Linux targets are
available. The default local quality gate is `APPLICABLE_LOCAL`.

## Dependency and deadlock review

R01 is the producer for the update command consumed later by R03, R05 and R07.
No parallel stream is used because CLI, application composition, workflow,
runner and documentation contracts must change atomically.

## Stop conditions

- invalid or unsupported source/target transition;
- missing live consent, target ownership or prerequisite evidence;
- backup/state protection cannot be established;
- update verification fails;
- raw secret-bearing output would enter evidence.
