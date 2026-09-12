# RC1-R04 Remaining Risks

- The replacement candidate-specific SonarCloud gate has not yet been
  observed as passed.
- trivy is unavailable locally, so container configuration evidence remains
  incomplete.
- The deterministic test-profile credential finding requires an explicit
  Sonar disposition and must not be generalized to production use.
- PR and Main workflow results may analyze different revisions; the exact SHA
  must remain part of every release decision.
