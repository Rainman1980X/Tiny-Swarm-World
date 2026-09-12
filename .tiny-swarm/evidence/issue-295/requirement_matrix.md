# CRED-08 requirement matrix

Source: GitHub #295, read in full on 2026-09-12; parent #277.
Baseline: `48de61e3`. Historical runs retain their own SHA and host.

| ID | Requirement | Type | Implementation / likely files | Verification | Status |
|---|---|---|---|---|---|
| C08-01 | Derive required services and UI/API applicability from actual profile; record expected principal and failure signal | contract | canonical Classic effective-model inventory | live_results_20260912.json reports.*.inventory; documented route table | VERIFIED |
| C08-02 | Actual UI logins for every applicable service on WSL2 and qualified native Linux | live | tests/e2e/classic/browser_e2e_contract.py | live_results_20260912.json four final baseline/post_restart reports.routes[].browser | VERIFIED |
| C08-03 | Prove effective identity/protected operation; Jenkins anonymous HTTP 200 never passes | security | existing browser/API clients | authenticated_service_contract regressions and all four reports.routes[jenkins].api; same-session whoAmI browser assertion | VERIFIED |
| C08-04 | Reject wrong credentials with bounded attempts and value-free evidence | security | canonical Classic tests | four final reports.routes[].api.invalid_rejected and six UI negative/positive sessions per phase | VERIFIED |
| C08-05 | Re-establish authenticated access after controlled approved restart; readiness insufficient | lifecycle | existing suites and #299 target orchestration | reports.wsl2_restart_reconciliation / native_restart operations + both spec_recovery rows + final post_restart reports | VERIFIED |
| C08-06 | Qualify storage before browser access; preserve evidence-root precedence, private directories; exclude raw screenshots/traces/secrets | security | secure_runtime_paths and browser evidence helpers | runner qualification regressions; four reports.storage_qualified_before_browser=true; test_results.md storage/cleanup | VERIFIED |
| C08-07 | Record actual tested SHA; rerun affected cases after code changes | provenance | per-host scenario reports | four clean reports.revision=d254b769; test_results.md e599-to-d254 affected reruns and evidence-only publication boundary | VERIFIED |
| C08-08 | Update #285/#293 evidence distinction and obtain independent completion audit | governance | issue evidence and documentation | documentation historical mapping; issue-285 continuation; completion_audit.md independent Requirement/Architecture/QA PASS | VERIFIED |
| C08-09 | Reuse existing credential contract/suites; preserve hexagonal architecture and avoid fallback identities | architecture | canonical Classic contract | canonical effective-model route derivation; architecture review; local 18 architecture tests / three contracts | VERIFIED |
| C08-10 | Reuse #298 native target, coordinate #299/#296; no competing provisioning | dependency | shared target/evidence | test_results.md native identity and dependency scope; historical mapping #296/#298/#299 | VERIFIED |
| C08-11 | Explicit live consent and qualified target; continue local work when live blocked | safety | guarded existing live mechanism | scope preflight and explicit complete-run consent; actual native trusted host access and report consent/storage flags | VERIFIED |
| C08-12 | Every live scenario records SHA, host/profile, commands, timestamps/duration, exit, LIVE state, readiness before/after, cleanup/recovery and redacted references | evidence | protected reports and published allowlisted summaries | live_results_20260912.json twelve timed component reports/manifest plus test_results.md command context and recovery limitations | VERIFIED |
| C08-13 | Full local gate; distinguish live/local/external; maintain six evidence files; missing/skipped/inconclusive never pass | quality | QUALITY.md and issue evidence | test_results.md full six-stage local gate 1974 tests, external candidate checks, fail-closed regressions; six evidence files | VERIFIED |

## Scope preflight

Ad-hoc issue implementation on dedicated `fix/cred-08-browser-acceptance-20260912`;
the active workflow file concerns #252 and is not executed or modified here.
Initial main checkout clean; no other worktrees or active lock files discovered.
Allowed scope: canonical `tests/e2e/classic/` acceptance contracts/tests, focused
live runner support if required, this issue's evidence and relevant prior evidence
links/documentation. Production changes require a reviewed root-cause finding.
Initial preflight selected read-only specialist reviews. Execution later split
the disjoint API helper and its tests into an isolated Git worktree/stream branch;
root consolidated those files and retained sole runtime/integration ownership.
No shared-runtime mutations were parallelized.

## Three Amigos loop 1

Requirement, architecture and QA independently identify public landing-page
markers bypassing credential submission and mixed skipped/passed aggregation.
Developer decision: repair those fail-open paths in the existing contract with
regressions before live execution; preserve canonical credential inputs and TLS.
Local gate: APPLICABLE_LOCAL. Browser/authentication/restart: APPLICABLE_LIVE.
Installation/reset: NOT_APPLICABLE to this bounded acceptance request.
The user's complete-run instruction authorizes bounded live acceptance and
controlled service restarts on existing test targets. Native SSH target requested;
no replacement provisioning inferred. No live success asserted by this matrix.
