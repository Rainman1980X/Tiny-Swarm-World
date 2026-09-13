# RC1-R05 Requirement Matrix

Issue: [#301](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/301).
Status: VERIFIED for the frozen product candidate c921e695. Executed hosted SHA
8eb5db33 has the identical complete Git tree. Exact SHAs and artifacts are in
[provenance](hosted-candidate-8eb5db33/provenance.json).

| ID | Requirement | Implementation and verification evidence | Status |
|---|---|---|---|
| R05-01 | Diagnose runner availability, ownership, labels and capabilities. | Runner 24 tsw-rc1-isolated; hosted qualification and qualified-empty-target.json | VERIFIED_HOSTED |
| R05-02 | Use protected environment, credentials, consent, timeouts and concurrency. | Existing workflow guards; accepted private 0600 configuration and 0700 evidence; run-summary.json | VERIFIED_LOCAL_AND_HOSTED |
| R05-03 | Keep orchestration in the canonical thin runner. | run_classic_acceptance.py invokes product commands and tests; no installer logic added to YAML | VERIFIED_LOCAL_AND_HOSTED |
| R05-04 | Execute fresh install, acceptance, reconcile, acceptance, update, acceptance and recovery. | Run 34725969899: all 14 operations passed, four complete authenticated suites | VERIFIED_HOSTED |
| R05-05 | Use an isolated approved target and retain failure diagnostics/cleanup. | Zero instances before setup; original target retained; initial bridge prerequisite failure retained and corrected; successful chain returns to A | VERIFIED_HOSTED |
| R05-06 | Produce a real successful candidate run. | Run 34725969899, LIVE_VERIFIED, exact executed 8eb5db33 | VERIFIED_HOSTED |
| R05-07 | Record actual SHA, host/runner, scenarios, duration and redacted artifacts. | Canonical run summary and four complete result.json packages with checksum manifest | VERIFIED_HOSTED |
| R05-08 | Propagate required failures and reject skipped success. | Setup failure 34725789727 stops the chain; blocked dispatch 34727197058 fails qualification and skips live execution | VERIFIED_HOSTED |
| R05-09 | Validate schedule/dispatch and missing consent/prerequisites. | Existing workflow contract verifies schedule, dispatch and owner fallback; approved/blocked manual runs and failed setup observed | VERIFIED_LOCAL_AND_HOSTED |
| R05-10 | Link current successful evidence into RC1. | Protected-runner row in documentation/release/rc1-decision.md | VERIFIED_DOCUMENTATION |
| R05-11 | Disposable tests do not require rotation reference. | Explicit --test-only; credential_rotation.status=not_applicable_test_only | VERIFIED_LOCAL_AND_HOSTED |
| R05-12 | Remove rotation variable use while preserving all other guards. | Existing workflow contract; successful qualification and blocked dispatch | VERIFIED_LOCAL_AND_HOSTED |
| R05-13 | Report test profile/rotation applicability without secret values. | execution_profile=disposable_test; allowlisted canonical summary and artifact review | VERIFIED_HOSTED |
| R05-14 | Explain GitHub variables and runner-local protected configuration. | Existing secure live/test guide, unchanged by this evidence follow-up | VERIFIED_DOCUMENTATION |

Scheduled wiring is validated locally; the real accepted execution was a manual
dispatch. No timer-triggered success is claimed. E09 owns the final all-row release
decision and final evidence integration SHA.
