# Acceptance Checklist: #285 / CRED-07

- [x] WSL2 fresh install reaches a real terminal result: reset/setup exit 0.
- [x] WSL2 checkout under `/mnt/*` succeeds on the standard internal-test path.
- [ ] Native Linux fresh install reaches a real terminal result.
- [x] Portainer authentication/access succeeds on WSL2; native counterpart is open.
- [x] Infisical bootstrap/login acceptance succeeds on WSL2; native counterpart is open.
- [x] Feasible other catalog services have WSL2 readiness/API checks.
- [ ] Complete WSL2 post-install authentication/UI acceptance; Jenkins identity and browser evidence remain open.
- [ ] Reconcile/rerun proves no credential drift.
- [x] WSL2 environment recreation resolves the documented default source model.
- [ ] A supported custom/Infisical override replaces the default.
- [ ] WSL2 Portainer restart/recovery proves authenticated access; readiness passed, post-restart authentication remains open.
- [x] Update remains not applicable because no canonical update workflow exists.
- [x] Protected evidence and installer output contain no raw credentials or authorization headers.
- [x] No blocked, skipped, partial, or degraded result is reported as PASS.
- [x] Final candidate passes the full local quality gate.
- [ ] Final matrix is fully observed for native Linux and override scopes.

Current decision: `BLOCKED`. WSL2 installation and the recorded bounded checks
passed. Native-Linux, override, drift, browser, Jenkins identity and
post-restart authentication evidence remain open.
