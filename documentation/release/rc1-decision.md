# Classic Public Beta RC1 Decision

Decision state: RC1_REJECTED_EVIDENCE_INCOMPLETE

This is the current evidence decision for the integrated work packages. It
does not close or reopen issues and does not authorize release publication.

| Work package | Owner issue | Local implementation | Required live/external result | Current state |
|---|---:|---|---|---|
| Canonical update | #297 | PR #321, local gates pass | WSL2/native update and recovery | OPEN |
| Native-Linux lifecycle | #298 | Closed baseline | Candidate-specific native run | HISTORICAL_BASELINE |
| WSL2 lifecycle/recovery | #299 | PR #322 | Fresh, reconcile, update, recovery, restart | OPEN |
| Sonar/CI quality | #300 | PR #323, local security checks | Passing candidate-specific Sonar gate | OPEN |
| Protected runner | #301 | PR #324 | Successful final-candidate self-hosted run | OPEN |
| Final evidence audit | #302 | This matrix and issue evidence | All rows independently reviewed | OPEN |
| Operator journey | #308 | Pending | Qualified target walkthrough | OPEN |
| Security evidence | #309 | Pending | Candidate-matched scans/dispositions | OPEN |
| Maintenance triage | #310 | Pending | Independent residual-risk review | OPEN |

Historical green runs remain useful for diagnosis when their SHA and scope
match, but they do not qualify the current candidate automatically. Missing,
queued, skipped, blocked or failed live/external checks remain non-pass.
