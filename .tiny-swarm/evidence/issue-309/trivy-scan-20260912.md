# RC1-R08 Trivy Scan Evidence

Date: 2026-09-12

Command:

```text
docker run --rm -v "$PWD/infra/config/compose:/scan:ro" \
  aquasec/trivy:latest config --exit-code 1 \
  --severity HIGH,CRITICAL /scan
```

Scanner image digest:

```text
aquasec/trivy:latest@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969
```

Result: **BLOCKED_BY_HIGH_FINDINGS**.

The scan detected `DS-0002` with severity HIGH in:

- `jenkins/image/Dockerfile`
- `service-access/dashboard/Dockerfile`
- `service-access/nginx/Dockerfile`

Each finding states that the Dockerfile does not declare a non-root `USER`.
No exception was created and no scanner rule was disabled. A remediation must
preserve the existing Jenkins and Service Access runtime contracts and must be
rescanned with candidate-matched image identities.
