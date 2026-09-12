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
| Protected runner | #301 | PR #324, disposable test profile configured without credential rotation; GitHub variables and Jenkins target image available, local Incus/LXC installation passed, full hosted lifecycle verified in [run 34719043422](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34719043422), controlled fail-closed dispatch verified in [run 34720172182](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34720172182) | None for #301 | VERIFIED |
| Final evidence audit | #302 | This matrix and issue evidence | All rows independently reviewed | OPEN |
| Operator journey | #308 | PR #326, local docs tests and AsciiDoc renders pass | Qualified target walkthrough | OPEN |
| Security evidence | #309 | PR #327, local Trivy HIGH/CRITICAL scan is clean after non-root remediation | Candidate-matched scans/dispositions | OPEN |
| Maintenance triage | #310 | PR #328, residual-risk review complete; focused follow-up #329 is open | Independent residual-risk review | OPEN |

Historical green runs remain useful for diagnosis when their SHA and scope
match, but they do not qualify the current candidate automatically. Missing,
queued, skipped, blocked or failed live/external checks remain non-pass.
