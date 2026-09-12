# RC1-R05 Remaining Risks

- Credential rotation is intentionally not applicable to the disposable test
  profile; a protected live profile still requires a non-secret rotation
  reference.
- A controlled required-scenario failure drill is still required before the
  issue can receive a PASS completion audit.
- The latest successful run used the candidate before the final target-owner
  evidence passthrough refinement; the passthrough is covered by the workflow
  contract test and should be observed on the next available hosted dispatch.
- Queued, cancelled, skipped or unavailable runs remain non-success.
- The successful run's redacted artifact upload and checksums were verified.
