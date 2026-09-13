# RC1-R05 Test Results

[Hosted run 34725969899](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725969899)
executed 8eb5db338aed9965a49ed6879198fd1053b97dcc on tsw-rc1-isolated.
Its whole tree a14e635dd22cb02fc063a319d73383f676572bca equals integrated product
candidate c921e69533450fba86d908e2990c106bef87769a. The run began at
2026-09-12 23:39:18 UTC and finished at 2026-09-13 00:15:06 UTC: LIVE_VERIFIED.

| Phase | Duration, seconds | Result |
|---|---:|---|
| Fresh setup from zero instances | 1723.846 | PASS |
| Initial authenticated acceptance | 134.130 | 25 live tests + 7 API checks, zero errors/failures/skips |
| Reconcile | 1.257 | PASS |
| Post-reconcile authenticated acceptance | 80.393 | 25 + 7, zero errors/failures/skips |
| Canonical distinct-image update | 13.346 | PASS |
| Post-update authenticated acceptance | 79.552 | 25 + 7, zero errors/failures/skips |
| Canonical recovery | 13.256 | PASS |
| Post-recovery authenticated acceptance | 81.902 | 25 + 7, zero errors/failures/skips |

The remaining diagnostics, platform verification and four Classic E2E operations
also passed; the canonical summary retains all 14 phase durations/exit codes.
Authenticated inner-suite durations above exclude the thin runner overhead.

[Failed setup 34725789727](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725789727)
retains the failed bridge prerequisite and stopped dependent work. No Incus node
was created before the operator corrected the isolated distribution/path inputs.
[Blocked dispatch 34727197058](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34727197058)
on evidence-only descendant 07cfd558 failed the explicit block guard and skipped
the live job; that skipped job is not counted as success.

The existing tests.test_ci_workflow_contract contract verifies schedule/dispatch,
owner fallback, private configuration inputs, protected environment and the
absence of the waived rotation variable. Full product quality and external
checks on c921e695 and 07cfd558 are recorded by R04. This evidence-only follow-up
uses git diff --check, verification-policy, artifact hashes, exact phase counts,
link validation and credential-pattern review; it does not rerun the unchanged
full runtime suite (QUALITY.md documentation-only exception).

[Provenance](hosted-candidate-8eb5db33/provenance.json),
[canonical summary](hosted-candidate-8eb5db33/run-summary.json), and
[artifact hashes](hosted-candidate-8eb5db33/sha256.json) are committed alongside
all four complete authenticated JSON packages and the actual blocked job record.
