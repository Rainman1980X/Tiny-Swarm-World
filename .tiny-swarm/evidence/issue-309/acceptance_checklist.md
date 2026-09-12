# RC1-R08 Acceptance Checklist

- [x] Classic service/image/dependency/admin/socket/network inventory recorded.
- [x] Reproducible dependency and SBOM checks executed.
- [x] Internal-test credential and override boundary documented.
- [x] Socket and admin access residual risk documented.
- [x] Trivy container-config scan executed and HIGH findings recorded.
- [x] DS-0002 findings remediated without a scanner exception.
- [x] Non-root `USER` remediation selected without changing Service Access
  port contracts.
- [ ] Candidate image digests recorded or justified.
- [ ] Candidate live reachability and admin boundaries verified.
- [ ] Independent security/evidence review returns PASS.
