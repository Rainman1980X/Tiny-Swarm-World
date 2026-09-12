# RC1-R03 Acceptance Checklist

- [x] Required lifecycle and recovery scenario matrix recorded.
- [x] Runner has ordered Fresh, Reconcile, Update and Recovery phases.
- [x] Required phase failures stop downstream mutation/acceptance.
- [x] Rollback recovery consumes RC1-R01 persisted state.
- [ ] Qualified protected WSL2 candidate run completed.
- [ ] Controlled partial deployment and managed service recovery observed.
- [ ] WSL2 restart boundary observed with restored identities, routes and readiness.
- [ ] Authenticated post-restart acceptance completed.
- [ ] Redacted final-candidate evidence published with SHA and timings.
- [ ] Independent completion audit returns `PASS`.
