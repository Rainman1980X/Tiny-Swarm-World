# Review Record: #285 / CRED-07

## Authorized live evidence review: 2026-09-09

An independent read-only reviewer inspected the safe run summaries and runner
code. It verified the corrected reconcile/authentication comparison, Jenkins
identity, post-restart Portainer authentication, explicit HTTP 401 default
denial during the override, restoration/cleanup, and final 27 browser tests
without failures or skips. Override and final browser runner hashes match;
run directories are `0700`, and no `.env` inputs remain in the evidence root.

Decision: WSL2 evidence accepted within its stated scope; overall `BLOCKED`.
Native-Linux installation and lifecycle parity are still missing. The matching
operator/Vault override satisfies the bounded configured-override scenario but
does not independently prove Vault-only precedence. Earlier failures remain
separate records. User live consent is now explicit and no longer a blocker.

The earlier review states below are retained as historical findings.

## Review state

`BLOCKED_PENDING_REQUIRED_LIVE_EVIDENCE`

Review method: the `issue-completion-auditor` skill was applied. A delegated
auditor returned the independent decision `BLOCKED`; the integration owner
also performed the required role-based fallback review and reconciled the
result with the current evidence.

The final candidate was reviewed for honest state classification after the
protected WSL2 run. The implementation and evidence now show:

- WSL2 `/mnt/d` fresh install: observed and green;
- protected installer evidence: observed and mode-verified;
- Portainer, Infisical, SonarQube and the other configured service phases:
  observed through the completed deployment workflow and redacted service
  checks;
- separate WSL2 reconcile and Portainer restart: observed and green;
- direct catalog-backed authentication for Portainer, Infisical, Nexus,
  SonarQube, Pulsar and Pulsar Manager: observed and recorded in
  `service_authentication.md`; Jenkins HTTP 200 remains inconclusive;
- native Linux: not available;
- supported override and full credential-drift comparison: not executed;
- browser acceptance: not executed.

The first PR review also found a SonarCloud new-code coverage failure (77.8%).
The missing evidence-root fallback branches are now covered by four direct
installer tests. The local quality gate now passes with 1908 tests and 18
skips. The external result was rechecked on 2026-09-08 for PR #293 at
`d474e2ebb907b846d25a922698304bf75fd35fed`: SonarCloud Code Analysis,
Locked Python quality gate, Conda Python 3.12 and Conda Python 3.13 all report
`SUCCESS`. SonarCloud completed at `2026-09-03T08:22:32Z`; its state is
`EXTERNAL_GATE_VERIFIED` for that commit only. This resolves the historical
external-check gap and does not establish any missing live acceptance.

The review therefore cannot issue a completion PASS. The 2026-09-09 independent
review also identified a locally repairable browser evidence-routing gap and
an inconclusive Jenkins authentication claim. These are corrected in the
continuation; required live acceptance still depends on target access, consent
and executed evidence. No merge or cleanup is permitted while the matrix
contains these open required scopes.

The independent repair review found no blocking code defect: both browser
entry paths qualify storage before network/browser access, retain non-live
behavior, and have meaningful storage regression coverage. This is a local
repair review, not an issue-completion PASS or GitHub approval.
