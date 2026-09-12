# Acceptance Checklist: #285 / CRED-07

Continuation: [CRED-08 / #295](../../../documentation/evidence/cred08-browser-acceptance.md)
maps these historical assertions to the stronger current browser/API contract.
The native host is now available; the unavailable-host statement below records
the historical #285 disposition, not current target availability. Current
both-host and post-restart acceptance is verified by #295 at `d254b769`; see
[executed results](../issue-295/test_results.md). This does not relabel historical
fresh-install, reconcile or override rows below.

- [x] WSL2 fresh install reaches a real terminal result: reset/setup exit 0.
- [x] WSL2 checkout under `/mnt/*` succeeds on the standard internal-test path.
- [ ] Native Linux fresh install reaches a real terminal result.
- [x] Portainer authentication/access succeeds on WSL2; native counterpart is open.
- [x] Infisical bootstrap/login acceptance succeeds on WSL2; native counterpart is open.
- [x] Feasible other catalog services have WSL2 readiness/API checks.
- [x] WSL2 API/browser acceptance includes Jenkins authenticated identity; see authorized run results and retained browser retry.
- [x] WSL2 reconcile/rerun proves no credential drift; native counterpart remains open.
- [x] WSL2 environment recreation resolves the documented default source model.
- [x] Supported Jenkins operator/Infisical override replaces the default; default HTTP 401 and restoration verified.
- [x] WSL2 Portainer restart/recovery proves authenticated access after restart.
- [x] Update remains not applicable because no canonical update workflow exists.
- [x] Protected evidence and installer output contain no raw credentials or authorization headers.
- [x] No blocked, skipped, partial, or degraded result is reported as PASS.
- [x] Final candidate passes the full local quality gate.
- [ ] Final matrix is fully observed for native Linux; override evidence is bounded to matching operator/Vault inputs.

Historical #285 decision: `BLOCKED`. Historical WSL2 installation plus authorized
WSL2 authentication, drift, override and recovery checks are evidenced.
Native-Linux installation and corresponding lifecycle acceptance remain open
because a sufficiently resourced native host/VM is unavailable.
