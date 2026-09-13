# Classic Public Beta RC1 Decision

Decision state: RC1_REJECTED_EVIDENCE_INCOMPLETE

This is the current evidence decision for the integrated work packages. It
does not close or reopen issues and does not authorize release publication.

| Work package | Owner issue | Local implementation | Required live/external result | Current state |
|---|---:|---|---|---|
| Canonical update | #297 | PR #321, local gates and candidate Sonar pass | WSL2/native update and recovery | OPEN |
| Native-Linux lifecycle | #298 | Closed baseline | Candidate-specific native run | HISTORICAL_BASELINE |
| WSL2 lifecycle/recovery | #299 | PR #322 | Fresh, reconcile, update, recovery, restart | OPEN |
| Sonar/CI quality | #300 | PR #323 stacked into PR #322; candidate Sonar pass is recorded on PR #321 | Passing candidate-specific Sonar gate on the integrated target | OPEN |
| Protected runner | #301 | Canonical runner and disposable test profile; qualified empty WSL target | [Fresh lifecycle 34725969899](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725969899) on 8eb5db33 (whole tree equals c921e695), 14 passed operations and four authenticated suites; [blocked dispatch 34727197058](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34727197058) failed before live mutation | VERIFIED |
| Final evidence audit | #302 | This matrix and issue evidence | All rows independently reviewed | OPEN |
| Operator journey | #308 | PR #326, local docs tests and AsciiDoc renders pass | Qualified target walkthrough | OPEN |
| Security evidence | #309 | PR #327, local Trivy HIGH/CRITICAL scan is clean after non-root remediation | Candidate-matched scans/dispositions | OPEN |
| Maintenance triage | #310 | PR #328, residual-risk review complete; focused follow-up #329 is open | Independent residual-risk review | OPEN |

Historical green runs remain useful for diagnosis when their SHA and scope
match, but they do not qualify the current candidate automatically. Missing,
queued, skipped, blocked or failed live/external checks remain non-pass.
