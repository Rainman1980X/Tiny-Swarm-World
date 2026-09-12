# RC1-R08 Remaining Risks

- Candidate registry images must be rebuilt, resolved and rescanned with
  immutable candidate digests.
- Version tags without resolved digests limit reproducibility for several
  configured images.
- Portainer/agent and Traefik Docker socket capability remains a reviewed
  internal-test risk.
- Candidate-specific live reachability and admin-boundary evidence remains
  open.
