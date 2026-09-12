# RC1-R08 Remaining Risks

- DS-0002 HIGH requires a non-root runtime decision for all three custom
  Dockerfiles. Service Access currently contracts internal HTTP on port 80;
  changing its NGINX user may require a coordinated internal-port and routing
  contract change.
- Version tags without resolved digests limit reproducibility for several
  configured images.
- Portainer/agent and Traefik Docker socket capability remains a reviewed
  internal-test risk.
- Candidate-specific live reachability and admin-boundary evidence remains
  open.
