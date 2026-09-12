# RC1-R01 Acceptance Checklist

- [x] Update/reconcile architecture decision recorded.
- [x] Canonical `platform update` help and validation verified.
- [x] Preview completes before any mutation.
- [x] Unsupported transition fails closed.
- [x] Backup and recovery behavior is executable and tested.
- [x] Repeated update is idempotent.
- [ ] WSL2 live update and post-update acceptance are `LIVE_VERIFIED`.
- [ ] Native-Linux live update and post-update acceptance are `LIVE_VERIFIED`.
- [x] Classic Nightly invokes the same canonical command.
- [ ] Redacted evidence identifies tested SHA, host/profile, scenario, timing,
  exit code and recovery outcome.
- [ ] Independent issue-completion audit returns `PASS` (live evidence is
  still pending).
