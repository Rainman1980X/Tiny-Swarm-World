# RC1-R05 Acceptance Checklist

- [x] Protected runner workflow contract reviewed.
- [x] Scoped credentials, consent, target ownership and concurrency guards retained.
- [x] Canonical runner owns lifecycle orchestration.
- [x] Redacted runner provenance fields added to terminal evidence.
- [x] Current intended runner and local Linux/Incus/Docker capabilities
  qualified.
- [ ] Isolated target and protected environment qualified.
- [ ] Full Fresh → Reconcile → Update → Recovery run succeeded.
- [ ] Controlled required-scenario failure produced a non-green result.
- [ ] Successful final-candidate run and artifact link recorded.
- [ ] Independent completion audit returns PASS.
