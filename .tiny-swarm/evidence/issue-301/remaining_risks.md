# RC1-R05 Remaining Risks

No open R05 acceptance requirement remains for the recorded product candidate.

- GitHub artifact retention is 14 days. The selected redacted JSON, complete
  authenticated phase reports, run IDs and checksum manifest are retained in Git.
- Historical runs on reused targets did not establish Fresh Install. Only the
  qualified zero-instance provenance and successful 34725969899 run support the
  current fresh-install claim.
- The source directory is Linux-native with ordinary public-source permissions.
  Its diagnostic reuses an evidence-directory assessment and therefore records
  evidence_mode_not_0700; the source gate checks filesystem classification.
  The actual secret and evidence paths independently passed their required
  0600/0700 ownership and mode checks. No source-directory 0700 claim is made.
- Scheduled wiring is covered by the existing workflow contract; the successful
  real lifecycle was manually dispatched. Queued or skipped jobs remain non-pass.
- The temporary target is retained for R03 restart tests. E09 tracks restoration
  of original runner routing and final harness cleanup; those later operations
  do not change the completed run's result.
- Final review uses the root-AGENTS role fallback after agent usage limits;
  it is not presented as a new independent subagent or human approval.
