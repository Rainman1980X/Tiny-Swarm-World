# RC1-R06 Requirement Matrix

Issue: #302 — Reconcile acceptance status and produce the final candidate evidence audit
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/302
Branch: feature/rc1-r06-final-evidence-audit-20260912

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| R06-01 | Map mandatory RC1 requirements to owner issues and evidence. | documentation/release/rc1-decision.md; issue evidence matrices | VERIFIED_LOCAL |
| R06-02 | Preserve historical issue closure reasons and scope. | release matrix; historical issue links | VERIFIED_LOCAL |
| R06-03 | Reconcile prior completion claims without erasing history. | Current decision marks old runs historical | VERIFIED_LOCAL |
| R06-04 | Select exact final candidate SHA after integration. | Candidate matrix records exact observed SHAs | OPEN_INTEGRATION |
| R06-05 | Verify lifecycle, recovery, restart, credentials and redaction. | R01/R03/R05 contracts | BLOCKED_LIVE |
| R06-06 | Verify quality, compatibility, Sonar and protected Nightly. | R04/R05 evidence | BLOCKED_EXTERNAL_LIVE |
| R06-07 | Rerun affected scenarios after candidate changes. | Re-run requirement recorded per issue | OPEN_INTEGRATION |
| R06-08 | Independent review checks every row. | completion audit files per issue | INCOMPLETE_PENDING |
| R06-09 | Publish one of the three exact RC1 decisions. | documentation/release/rc1-decision.md | VERIFIED_LOCAL |
| R06-10 | Align release readiness documentation and limitations. | decision matrix and issue evidence | VERIFIED_LOCAL_PENDING_REVIEW |

The only current decision is RC1_REJECTED_EVIDENCE_INCOMPLETE.
