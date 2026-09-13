# RC1-R04 Requirement Matrix

Issue: [#300](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/300).
Candidate: `c921e69533450fba86d908e2990c106bef87769a` (integrated PR #335).
[Machine-readable evidence](candidate-c921e695/provenance.json) retains executed
revisions, workflow metadata, separate PR/main results and scan input hashes.

| ID | Requirement | Implementation evidence | Verification evidence | Status |
|---|---|---|---|---|
| R04-01 | Inspect failing conditions, thresholds, analysis and SHA. | implementation_summary.md; historical release matrix | Faraday diagnosis of analysis b683560c-2f9a-4179-a6f3-aca64e2f6ec2; run 34720818090 | VERIFIED_EXTERNAL_DIAGNOSIS |
| R04-02 | Correct the smallest reproduced source/test cause. | PR #330; private CA copied with shutil.copyfile | 15 TLS regressions; preserved permissions/path checks; full quality | VERIFIED_LOCAL |
| R04-03 | Prove scanner checkout and analysis revision. | Existing sonar.scm.revision and gate wait | Actual checkout/SCM lines for PR 34725802800 and main 34726472444 | EXTERNAL_GATE_VERIFIED |
| R04-04 | Observe a new passing candidate/main Sonar gate. | No rules or source scope disabled | Independent executions 34725802800 and 34726472444 both waited for PASSED | EXTERNAL_GATE_VERIFIED |
| R04-05 | Verify required PR/main quality and every supported Python version. | Unchanged quality/compatibility workflows | PR 34725658814/34725658760; main 34726339297/34726339319, Python 3.12 and 3.13 | VERIFIED_CI |
| R04-06 | Distinguish failed, unavailable and skipped states. | Existing fail-closed workflow and state policy | Historical failure retained; PR main-job skips never counted as main success | VERIFIED_LOCAL_AND_EXTERNAL |
| R04-07 | Preserve rules, meaningful scope and failure propagation. | PR #330 diff and unchanged gate configuration | TLS tests, workflow contracts and actual waited gates | VERIFIED_LOCAL_AND_EXTERNAL |
| R04-08 | Record successful replacement URLs and exact revisions. | documentation/release/rc1-candidate-evidence.md | provenance.json includes all six final-candidate CI runs | VERIFIED_EXTERNAL |
| R04-09 | Execute dependency/SBOM/container-config checks with tool and input provenance. | Existing tools/security_gate.py and scan policy | Fresh scans on 8eb5db33; whole Git tree equals c921e695; 13 dependencies, three Dockerfiles, zero HIGH/CRITICAL config findings | VERIFIED_LOCAL |

R04 is complete for this candidate. Evidence-only descendants must retain product
scope equivalence and receive their own required hosted checks; E09 owns the final
integrated revision and overall release decision.
