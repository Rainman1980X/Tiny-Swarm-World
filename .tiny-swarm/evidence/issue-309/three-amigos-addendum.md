# RC1-R08 Three-Amigos Security Finding Addendum

Finding: Trivy DS-0002 HIGH in three custom Dockerfiles.

Requirement lead: the finding is within the security acceptance scope and
cannot be marked as a successful scan solely because dependency and SBOM
checks pass.

System architect: adding `USER nginx` to the Service Access images may break
the current container port-80 and dashboard upstream contracts. A safe fix
needs either a verified non-root low-port design or a coordinated internal
port change across compose, routing, readiness and tests. Jenkins can be
reviewed independently because its official image already has a `jenkins`
runtime user.

Test/evidence reviewer: the finding is reproducible with the recorded scanner
digest. Any remediation requires Dockerfile build/start verification, route
and readiness regression tests, and a candidate-matched rescan.

Decision: **REQUIRES_REFINEMENT** for the Service Access remediation choice;
release security evidence remains blocked until the choice is made and
verified.
