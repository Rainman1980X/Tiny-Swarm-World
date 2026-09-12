# RC1-R04 Requirement Matrix

Issue: #300 — Repair the actual main Sonar quality gate and verify candidate-specific CI results
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/300
Repair branch: `fix/rc1-r04-sonar-20260913`

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R04-01 | Inspect actual failing conditions, measures, analysis and SHA. | documentation/release/rc1-candidate-evidence.md | Analysis b683560c-2f9a-4179-a6f3-aca64e2f6ec2; run 34720818090 | VERIFIED_EXTERNAL_DIAGNOSIS |
| R04-02 | Classify and correct smallest reproducible code/test causes. | Private managed CA bundle copied explicitly with shutil.copyfile | 15 focused TLS tests including CA/bundle byte equality; local lint | VERIFIED_LOCAL |
| R04-03 | Preserve scanner checkout and analysis provenance. | Existing sonar.scm.revision plus candidate matrix | Workflow/run/analysis identifiers recorded | VERIFIED_LOCAL |
| R04-04 | Observe a passing candidate-specific Sonar gate. | Existing wait/fail-closed workflow | Replacement analysis pending | BLOCKED_EXTERNAL |
| R04-05 | Preserve Python quality and compatibility checks. | Existing workflows; no weakening | Candidate-specific hosted checks pending for this branch | VERIFIED_LOCAL_PENDING_CI |
| R04-06 | Keep failure, unavailable and skipped states distinct. | Existing workflow conditions and evidence policy | Static workflow contract tests | VERIFIED_LOCAL |
| R04-07 | Avoid continue-on-error, reduced scope or rule disabling. | No such changes introduced | Diff review and workflow contract | VERIFIED_LOCAL |
| R04-08 | Record replacement run and exact SHA in release matrix. | Release matrix added | Replacement run pending | VERIFIED_LOCAL_PENDING_EXTERNAL |

Acceptance remains incomplete until the integrated candidate receives a newly
observed passing SonarCloud quality gate.
