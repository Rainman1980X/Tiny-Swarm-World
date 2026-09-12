# RC1-R04 Test Results

- TLS, credential and related regression tests: **70 passed**.
- Ruff lint: **PASS**.
- git diff --check: **PASS**.
- Local dependency audit: **PASS**, no known vulnerabilities.
- Local SBOM generation: **PASS**, CycloneDX output generated in ignored
  local evidence storage.
- Local container-config scan: **BLOCKED**, trivy is unavailable.
- Hosted SonarCloud replacement analysis: pending after PR publication.

The local security checks do not substitute for the candidate-specific
SonarCloud quality gate.
