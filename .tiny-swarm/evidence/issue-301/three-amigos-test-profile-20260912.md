# Three-Amigos Gate: Disposable Classic Test Profile

Date: 2026-09-12
Issue: #301 follow-up requirements R05-11 through R05-14
Decision: PROCEED_WITH_ACCEPTED_ASSUMPTIONS

## Requirement lead

The requested scope is limited to the disposable Incus/LXC test target. The
workflow must stop requiring `TSW_CLASSIC_CREDENTIAL_ROTATION_REFERENCE` and
must pass an explicit test-only mode. Consent, target ownership, secure
runner-local configuration, update inputs, evidence and the complete lifecycle
remain in scope. Credentials remain outside Git and outside evidence.

## System architect

The change stays in the existing thin live runner and does not move command,
filesystem or provider logic into the workflow. Test-only is an explicit
execution profile, so an unmarked protected/live invocation still requires a
valid rotation reference. The Linux-native 0600 env-file guard remains active.

## Python and tester

The parser, precondition and redacted terminal summary are directly testable
without mutating infrastructure. Contract tests will prove that the workflow
uses test-only mode, does not reference the rotation variable, and records the
profile/rotation state safely. Targeted tests and the repository quality gate
are the required local checks.

## Accepted assumptions and stop conditions

- The existing GitHub environment and runner labels remain in use; renaming
  them would be a separate governance change.
- GitHub variables contain paths, ownership labels and update image metadata;
  the test credentials stay only in the runner-local secure env file.
- The hosted lifecycle is now verified by run 34719043422; the controlled
  blocked-dispatch behavior is verified by run 34720172182.
- No protected/live workflow is allowed to bypass rotation unless it opts into
  the explicit test-only profile.
