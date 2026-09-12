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

Result before the Jenkins remediation: **BLOCKED_BY_HIGH_FINDINGS**.

The scan detected `DS-0002` with severity HIGH in:

- `jenkins/image/Dockerfile`
- `service-access/dashboard/Dockerfile`
- `service-access/nginx/Dockerfile`

Each finding states that the Dockerfile does not declare a non-root `USER`.
No exception was created and no scanner rule was disabled. A remediation must
preserve the existing Jenkins and Service Access runtime contracts and must be
rescanned with candidate-matched image identities.

Follow-up: Jenkins now declares `USER jenkins`, matching the official image's
runtime user contract. Both Service Access images now declare `USER nginx`.
An isolated image run preserved their existing internal ports. The follow-up
scan reported 0 HIGH/CRITICAL findings for all three Dockerfiles. The scan is
source/config evidence; candidate-built image vulnerability evidence remains
required separately.

Local image smoke identities:

- `tsw-service-access-dashboard-rootless-test`: `sha256:f86ce3a9b61db2ec750669e9002537da9b591534f07839e61a780fb8ba2b2573`
- `tsw-service-access-nginx-rootless-test`: `sha256:23dd00ec844b57765eea0036d50c63d720c0fa022bfe67a0a620d71e83317f1a`
