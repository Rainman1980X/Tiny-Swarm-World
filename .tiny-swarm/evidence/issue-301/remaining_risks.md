# RC1-R05 Remaining Risks

- Repository live variables, target ownership and the protected environment
  still need to be configured for a complete hosted observation.
- The local test installation passed, but the full Fresh → Reconcile → Update
  → Recovery lifecycle can only be accepted after a protected isolated target
  run reaches every required phase.
- Queued, cancelled, skipped or unavailable runs remain non-success.
- Retained diagnostics and artifact upload still need to be checked on the
  protected runner's real failure and successful final-candidate runs.
