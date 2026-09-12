# RC1-R08 Requirement Matrix

Issue: #309 — Qualify Classic security boundaries and retain release supply-chain evidence
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/309
Branch: feature/rc1-r08-security-evidence-20260912

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| R08-01 | Inventory services, images, dependencies, admin routes, sockets and networks. | documentation/security/rc1-classic-security-evidence.md | VERIFIED_LOCAL |
| R08-02 | Execute dependency/SBOM/container-config checks with versions and results. | issue test_results.md; trivy-scan-20260912.md | VERIFIED_LOCAL_WITH_FINDING |
| R08-03 | Classify findings by profile applicability and disposition. | Security procedure; R04 Sonar disposition | VERIFIED_LOCAL_PENDING_REVIEW |
| R08-04 | Verify/document socket and admin boundaries. | Security procedure and existing compose contracts | VERIFIED_LOCAL |
| R08-05 | Record reproducible image identities and digest limitation. | Static inventory; candidate digest capture pending | VERIFIED_LOCAL_PENDING_CANDIDATE |
| R08-06 | Confirm internal-test credential and override boundary. | Existing credential ADR and security procedure | VERIFIED_LOCAL |
| R08-07 | Define reproducible security procedure and pass/block rules. | Security procedure | VERIFIED_LOCAL |
| R08-08 | Feed reports/dispositions to R06; unresolved blockers prevent acceptance. | R06 decision matrix | OPEN_REVIEW |

The container-config scan is now available but reports unresolved HIGH
DS-0002 findings. Candidate-matched live image evidence also remains open, so
the issue remains incomplete.
