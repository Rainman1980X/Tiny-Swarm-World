# Classic RC1 Security Evidence Procedure

This procedure qualifies the internal-test Classic profile at a declared
candidate SHA. It records image references, administrative surfaces, socket
mounts, network/port contracts, credential boundaries and scan outcomes
without storing secret values or fingerprints.

## Static inventory

| Area | Current contract | Evidence source |
|---|---|---|
| Image references | Compose service images and approved overrides; immutable digest where configured | infra/config/compose and services.yml |
| Python dependencies | requirements.lock | requirements.lock |
| Admin surfaces | Portainer, Nexus, Jenkins, SonarQube, Pulsar Manager, Infisical and Service Access routes | infra/config/ports.yaml and services.yml |
| Docker socket | Portainer and agent mount the socket; Traefik uses a read-only socket mount | compose files for portainer and traefik |
| Credential source | Operator overrides or internal-test catalog/Infisical contracts | arc42 credential contracts and secret manifest |
| Reachability | Published ports and routed hostnames are profile-specific | ports.yaml and access-model evidence |

A read-only socket mount does not provide Docker API authorization. The
socket and administrative surfaces therefore remain explicit residual risks
for the isolated internal-test profile.

## Reproducible checks

Run from the candidate checkout:

    python3 tools/security_gate.py dependencies
    python3 tools/security_gate.py sbom
    python3 tools/security_gate.py container-config

Record tool versions, candidate SHA, date, result and redacted output location.
The first two checks are local prerequisites; the container-config check
requires Trivy. Missing tools and scans are non-success states.

## Disposition rules

Applicable release-blocking findings require a focused correction and a
candidate-matched rescan. Internal-test-only deterministic credentials may be
retained only with their non-production scope and override boundary recorded.
No scanner rule is disabled and no external scanner is added to the default
quality gate by this procedure.
