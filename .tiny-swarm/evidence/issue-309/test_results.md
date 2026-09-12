# RC1-R08 Test Results

- pip-audit 2.10.1 dependency check: **PASS**, no known vulnerabilities.
- SBOM generation: **PASS**, CycloneDX report generated in ignored local
  evidence storage.
- Trivy container-config check: **BLOCKED**, executable unavailable.
- Static compose/ports/credential inventory review: **PASS**.
- git diff --check: **PASS**.
- No live network/admin boundary or candidate image digest run was executed.
