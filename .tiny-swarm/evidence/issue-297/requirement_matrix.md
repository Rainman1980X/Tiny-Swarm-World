# RC1-R01 Requirement Matrix

Issue: [#297](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/297).
Frozen product candidate: `c921e69533450fba86d908e2990c106bef87769a`. Status: `DONE`; audit: `PASS`.

The existing twelve requirement IDs are retained. Original independent findings
and repair history remain in `historical-repair-publication/`.

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R01-01 | Define update versus reconcile and a safe reversible scenario. | ADR classic update contract; same-binary marker image A to distinct B. | ADR, marker-transition.json and focused update tests. | VERIFIED |
| R01-02 | Canonical command has help and argument validation. | Existing platform update CLI. | tests.test_classic_update_cli; full candidate quality. | VERIFIED |
| R01-03 | Mutating update requires explicit live consent and truthful refusal. | Existing CLI guard and protected canonical runner. | CLI consent regressions and blocked hosted run in issue-301. | VERIFIED |
| R01-04 | Preview validates intended transition before mutation. | Typed plans, configured membership and live runtime preflight. | Preview, source mismatch and blocked-transition regressions. | VERIFIED |
| R01-05 | Unsupported, malformed or unavailable transitions do not mutate. | Runtime port, strict adapter schema and typed errors. | Malformed task/state, unknown status and invalid-argument regressions. | VERIFIED |
| R01-06 | Executable state protection and original-direction recovery. | Atomic private update plan; platform update --recover; no service-data migration. | Both-host recovery, repeat-recovery and original-plan equality artifacts. | VERIFIED |
| R01-07 | Apply and verify supported change on healthy WSL2 and native Linux. | Existing deployment ports and runtime task convergence. | Hosted WSL 34725969899; native full c921 lifecycle and bedb scoped run. | VERIFIED |
| R01-08 | Preserve identities, persistent data, unrelated configuration and credentials. | Selected Jenkins stack/image boundary; no global Infisical re-bootstrap. | Both-host continuity booleans; no changed unrelated ServiceSpecs; all seven API checks. | VERIFIED |
| R01-09 | Repeated updates are idempotent and failed rollout recovers safely. | Original recovery plan retained across repeat/no-op and failure. | WSL fresh-idempotency.json; native scopefix-comparison.json; both typed rollout_failed sequences. | VERIFIED |
| R01-10 | Canonical post-update service/browser/API acceptance on both hosts. | Existing Classic authenticated acceptance runner. | Each update/recovery phase has 25 live tests, including nine browser tests, plus seven API checks; zero errors/failures/skips. | VERIFIED |
| R01-11 | Host lifecycle and Classic Nightly use the same command. | tools/live/run_classic_acceptance.py and nightly-classic-live.yml. | Actual 14-operation hosted WSL and manual native chains; runner contract tests. | VERIFIED |
| R01-12 | Regression, documentation and redacted live evidence complete. | Merged PRs 333/334/335, ADR and usage update instructions; checksummed packages. | 2066-test candidate quality, exact candidate CI/Sonar and this completion audit. | VERIFIED |

R01-F01 through R01-F05 are resolved by the mapped runtime observer, original
recovery-state preservation, strict schema, complete runner summaries and ADR
changes. The actual cross-host evidence above closes their former live gaps.
