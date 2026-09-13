# RC1-R01 Test Results

Frozen product `c921e69533450fba86d908e2990c106bef87769a`; date 2026-09-13. Local, live and external checks remain distinct.

| Executed evidence | Result |
|---|---|
| Full local quality, Python 3.12.14, product-equivalent PR335 tree | PASS: 2066 tests, 18 explicit live/optional skips; 674 typed files; three import contracts and 18 architecture tests |
| Focused typed-observation workflow/adapter regressions | PASS: 41 tests |
| Selected-stack composition regressions | PASS: 104 tests |
| WSL hosted fresh chain [34725969899](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725969899) | LIVE_VERIFIED, all 14 operations exit zero |
| Native fresh lifecycle 20260912T235814.253797Z | LIVE_VERIFIED, all 14 operations exit zero |
| Native original scoped update/repeat/recover/repeat 20260912T233137Z | PASS, ten steps; original recovery plan and repeat task/container identity retained |
| WSL fresh-idempotency.json | PASS; update/recovery repeats no-op, original plan unchanged |
| Native fault 20260912T233437Z and WSL fault 20260913T001657Z | Expected update exit 1 with typed rollout_failed; recovery exit zero, authenticated acceptance and repeat recovery pass |

Every successful required authenticated phase has 25 live tests (eight readiness,
nine browser, eight readiness afterward) and seven API checks, zero failures/errors/
skips. Full hosted authentication artifacts are in
[issue-301](../issue-301/hosted-candidate-8eb5db33/); native phase summaries and
both-host scoped results are checksummed in this package.

Candidate main quality [34726339297](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339297),
compatibility [34726339319](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339319)
and Sonar [34726472444](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726472444)
passed on actual candidate c921e695. The exact Sonar SCM revision and scan provenance
are recorded in [R04](../issue-300/candidate-c921e695/).

Retained full-quality log SHA-256: `df816b36440c8a8d6f925c019a94d31fd0609b5244e4fde05a12c142886018fc`.
This documentation-only publication uses diff/policy, source-equivalence, JSON
assertions, manifest hashes, link and redaction checks. Repeating the full runtime
suite solely for artifact packaging is omitted under QUALITY.md; no new full-suite
execution is claimed. PR-specific hosted checks are observed before merge.

Earlier failed native verification 20260912T232414Z remains in the package. Its
changing-snapshot cause is inferred, not proven; later deterministic regressions
and actual successful reruns establish the repaired behavior. Earlier incomplete
reports remain dated historical evidence, not current PASS substitutes.
