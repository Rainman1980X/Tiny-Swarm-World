# RC1-R05 Remaining Risks

- Credential rotation is intentionally not applicable to the disposable test
  profile; a protected live profile still requires a non-secret rotation
  reference.
- The latest successful run used the candidate before the final target-owner
  evidence passthrough refinement; the passthrough is covered by the workflow
  contract test. The controlled blocked dispatch was executed after that
  refinement, but it stops before the live chain and therefore does not
  exercise the successful lifecycle on that later metadata revision.
- Queued, cancelled, skipped or unavailable runs remain non-success.
- The successful run's redacted artifact upload and checksums were verified.
