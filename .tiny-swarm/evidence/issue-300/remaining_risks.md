# RC1-R04 Remaining Risks

- The new source expression must pass the actual candidate-specific Sonar gate.
- Historical PR #323 has no observable pre-merge checks; retain this gap. The
  repair PR requires observed quality, compatibility and Sonar before merge.
- Trivy is available as a pinned local container. The prior successful config
  scan lacks exact candidate provenance; repeat it for the integrated SHA.
- Old hosted artifacts contain multiple attempts and SHAs. Select the exact
  candidate/run before reading any success result.
- Candidate image vulnerability results are distinct from config scan results.
