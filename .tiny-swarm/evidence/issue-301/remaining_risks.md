# RC1-R05 Remaining Risks

- Repository live variables, target ownership, update image references and the
  protected environment still need to be configured for a complete hosted
  observation. Credential rotation is intentionally not applicable to the
  disposable test profile.
- The hosted runner currently reaches qualification but its setup preflight
  fails before lifecycle mutation; the runner/Incus target state needs repair
  or a further diagnostic run before hosted acceptance.
- The local test installation passed, but the full Fresh → Reconcile → Update
  → Recovery lifecycle can only be accepted after a protected isolated target
  run reaches every required phase.
- Queued, cancelled, skipped or unavailable runs remain non-success.
- Retained diagnostics and artifact upload still need to be checked on the
  protected runner's real failure and successful final-candidate runs.
