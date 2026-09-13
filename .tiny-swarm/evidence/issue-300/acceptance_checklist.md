# RC1-R04 Acceptance Checklist

- [x] Actual failing conditions, thresholds, analysis ID and SHA recorded.
- [x] Focused source repair and CA/bundle regression merged in PR #330.
- [x] Actual scanner checkout and SCM revision verified separately from workflow metadata.
- [x] No rules, meaningful scope or failure propagation weakened.
- [x] Fresh dependency, SBOM and container-config checks retained with versions and hashes.
- [x] New candidate-specific PR Sonar gate passed before PR #335 merged.
- [x] Independent post-integration main Sonar gate passed.
- [x] PR/main quality and Python 3.12/3.13 compatibility passed.
- [x] Historical failure and unavailable/skipped states remain distinct.
- [x] Replacement URLs and analyzed SHA recorded in the release matrix.
- [x] Completion audit passed using the explicitly recorded root-AGENTS role fallback and prior independent diagnosis.
