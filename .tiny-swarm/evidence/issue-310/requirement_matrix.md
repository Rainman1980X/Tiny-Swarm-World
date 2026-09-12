# RC1-R09 Requirement Matrix

Issue: #310 — Triage central-module maintenance risks and define focused follow-up work
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/310
Review branch: `docs/rc1-r09-independent-review-20260913`

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| R09-01 | Inspect central modules against responsibilities, ports and tests. | documentation/arc42/05_analysis/rc1-maintenance-triage.adoc | VERIFIED_LOCAL |
| R09-02 | Classify observations as addressed, acceptable, debt or blocker. | Triage disposition table | VERIFIED_LOCAL |
| R09-03 | Define bounded follow-up with files, contracts, regressions and benefit. | Bounded follow-up section; issue #329 | VERIFIED_LOCAL |
| R09-04 | Route concrete blockers to functional owners. | Three update defects registered in #294/#297 (2026-09-13 review section, linked baseline reproducers); #299/#301 consume | VERIFIED_LOCAL |
| R09-05 | Preserve stable composition/import/patch contracts. | No product source change; existing architecture tests | VERIFIED_LOCAL |
| R09-06 | Independent architecture/test review and residual risk for R06. | Independent Poincare/Faraday reviews; R06 acknowledgement in remaining_risks.md | VERIFIED_INDEPENDENT_REVIEW |

Completion is triage completion; the future refactor is not an RC1 gate.
