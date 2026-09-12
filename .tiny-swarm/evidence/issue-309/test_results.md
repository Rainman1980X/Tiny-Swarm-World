# RC1-R08 Test Results

- pip-audit 2.10.1 dependency check: **PASS**, no known vulnerabilities.
- SBOM generation: **PASS**, CycloneDX report generated in ignored local
  evidence storage.
- Initial Trivy container-config check: **HIGH FINDING**, executed with
  `aquasec/trivy:latest` at digest
  `sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969`;
  DS-0002 was reported for the Jenkins, Service Access dashboard and Service
  Access NGINX Dockerfiles. See `trivy-scan-20260912.md`.
- Remediation: all three custom Dockerfiles now declare non-root users;
  isolated image smoke check preserved Service Access ports 80 and 8086.
- Follow-up Trivy container-config check: **PASS**, 0 HIGH/CRITICAL findings
  with the same scanner digest.
- Static compose/ports/credential inventory review: **PASS**.
- git diff --check: **PASS**.
- No live network/admin boundary or candidate image digest run was executed.
