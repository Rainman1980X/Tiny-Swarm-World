# RC1-R04 Remaining Risks

No open R04 acceptance requirement remains for candidate c921e695.

- Historical PR #323 lacks observable pre-merge checks. This gap is retained;
  the final product candidate has its own observed PR and post-merge main checks.
- Three Dockerfile configuration checks and the locked Python dependency audit
  do not establish that built container images are vulnerability-free. R08 owns
  running image inventory, admin/network boundaries and applicable dispositions.
- The first scan-container attempt failed before scanning because the operator
  WSL handover removed the original Docker bridge. The successful pinned-scanner
  retry used host networking with read-only inputs and no Docker socket; both
  outcomes are distinguished in provenance.
- Real reviewers reached the session usage limit after the independent source
  reviews. Final evidence reconciliation used the root-AGENTS role fallback;
  it is not represented as a new independent human or subagent approval.
- A later source/configuration change requires fresh matching verification.
  E09 must bind the final evidence-only integration SHA to its own hosted gates.
