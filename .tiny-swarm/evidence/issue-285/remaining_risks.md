# Remaining Risks and Scope Boundaries: #285 / CRED-07

- No separate native-Linux host or VM was available. Incus containers managed
  from WSL2 cannot substitute for native-Linux host evidence.
- The custom/Infisical override scenario was not run. It requires an
  operator-owned WSL-native `0600` credential file and a non-secret
  credential-rotation reference; neither was supplied.
- The separate reconcile run passed, but a before/after credential-source or
  value-equivalence comparison was not captured, so credential-drift
  acceptance remains open.
- Browser acceptance was not run. Installer/API readiness and service access
  are not browser evidence.
- Historical failed attempts are retained only as redacted diagnostic history;
  they are not passes. The final WSL2 run is the protected candidate.
- The authorized Incus test environment is still running after the successful
  proof. No production environment was targeted.

These gaps keep the issue and PR in `BLOCKED` state. No merge or branch cleanup
is authorized until the missing required evidence is supplied and reviewed.

## Completion recheck: 2026-09-08

The independent completion audit confirmed these concrete requirements for
the next authorized run:

- Supply a native-Linux host or VM and explicit consent for the selected
  installation/reset and lifecycle scenarios. Historical WSL2 consent and
  evidence do not identify or authorize a new native-Linux target.
- Compare resolved sources and value equivalence in memory before and after
  reconcile, then authenticate again. Persist source labels and boolean
  comparison results only.
- Use a supported custom or Infisical override on a suitable test lifecycle;
  changing an environment variable on an existing installation is not proof
  of rotation. Fresh test override values may be generated locally after live
  authorization; the user need not transmit secret values.
- The guarded Classic acceptance runner separately requires a factual
  rotation/revocation reference for the previously exposed credentials,
  according to `documentation/evidence/wsl2-secure-live-path.md`. A new test
  value or arbitrary run identifier does not prove revocation.
- Execute successful UI logins required by parent EPIC #277. Before the
  browser run, resolve its evidence location: the browser contract currently
  writes under the checkout and does not consume `TSW_LIVE_EVIDENCE_ROOT`.
  A protected execution arrangement or a verified routing fix is required;
  the installer's protected evidence root does not cover browser artifacts.
- Verify authentication after restart, and for Jenkins record an authenticated
  identity or an unequivocally authorized operation. HTTP 200 from `/whoAmI`
  alone is insufficient to distinguish an anonymous response.

These are pending verification steps, not executed results. The historical
SonarCloud gap has been resolved for `d474e2eb` as recorded in `review.md`.
