# RC1-R04 Requirement Matrix

Issue: #300 — Repair the actual main Sonar quality gate and verify candidate-specific CI results
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/300
Branch: feature/rc1-r04-sonar-gate-20260912

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R04-01 | Inspect actual failing conditions, measures, analysis and SHA. | documentation/release/rc1-candidate-evidence.md | SonarCloud API and run 34686480442 | VERIFIED_EXTERNAL_DIAGNOSIS |
| R04-02 | Classify and correct smallest reproducible code/test causes. | TLS generated-path mapping and credential test assertion | Focused 70-test regression; local lint | VERIFIED_LOCAL |
| R04-03 | Preserve scanner checkout and analysis provenance. | Existing sonar.scm.revision plus candidate matrix | Workflow/run/analysis identifiers recorded | VERIFIED_LOCAL |
| R04-04 | Observe a passing candidate-specific Sonar gate. | Existing wait/fail-closed workflow | Replacement analysis pending | BLOCKED_EXTERNAL |
| R04-05 | Preserve Python quality and compatibility checks. | Existing workflows; no weakening | Candidate-specific hosted checks pending for this branch | VERIFIED_LOCAL_PENDING_CI |
| R04-06 | Keep failure, unavailable and skipped states distinct. | Existing workflow conditions and evidence policy | Static workflow contract tests | VERIFIED_LOCAL |
| R04-07 | Avoid continue-on-error, reduced scope or rule disabling. | No such changes introduced | Diff review and workflow contract | VERIFIED_LOCAL |
| R04-08 | Record replacement run and exact SHA in release matrix. | Release matrix added | Replacement run pending | VERIFIED_LOCAL_PENDING_EXTERNAL |

The issue remains open until the integrated candidate receives a newly
observed passing SonarCloud quality gate.
