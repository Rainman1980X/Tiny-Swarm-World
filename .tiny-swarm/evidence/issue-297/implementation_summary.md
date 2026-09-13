# RC1-R01 Implementation Summary

Status: DONE. Candidate `c921e69533450fba86d908e2990c106bef87769a`. This evidence completion changes no product code.
PRs #333, #334 and #335 implement the canonical observed update, original-direction
recovery, complete authenticated runner contract, selected-stack scope and bounded
retry for a typed changing post-apply observation. Earlier independent reviewers
Poincare and Laplace identified and reviewed the original repair boundary.

The supported proof is Jenkins A to a distinct marker-only B, with the same binary
and data format. Both hosts execute canonical update and recovery, real task/image
convergence, repeated no-op operations and controlled failed rollout recovery.
Private persistence/configuration comparisons emit equality flags only. Complete
authenticated acceptance passes after each required phase. The native original
scope test deliberately retains the environment without unrelated TLS references,
verifying the selected-stack fix rather than concealing it with extra configuration.

WSL hosted execution `8eb5db338aed9965a49ed6879198fd1053b97dcc` has exactly the candidate Git tree. Additional WSL
idempotency/fault tests execute `c921e69533450fba86d908e2990c106bef87769a`. Native scoped execution `bedb0c9f1d5f2fdfddf6f14624242a18fce55f25` differs only
in documentation/workflow evidence; `native-candidate-bedb0c9f/provenance.json`
records every differing path. Fresh native full lifecycle executes `c921e69533450fba86d908e2990c106bef87769a` itself.
These are actual executed SHAs, not relabeled runs.

R02/R03 own whole-host restart and R06 owns final release acceptance. R01 completion
does not claim those separate results or publication of a release.
