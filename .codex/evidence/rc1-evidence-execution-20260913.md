# RC1 evidence execution preflight

Date: 2026-09-13. Execution owner: Codex / tiny-swarm-world-lead-architect.
Selected workflow: `documentation/workflow/workflow.index.md` and its issue
workflows. The old Issue-252 active workflow is historical for this execution.
Branch: `feature/rc1-evidence-execution-20260912`, isolated execution worktree.

## S3 / S3D decision

The authoring checkout was clean at `e320179f7606f060ac3655144933af68307f8903`.
The integrated product baseline is `9db135710829851961be534662ff3796acbf44bc`.
No product changes separate these revisions. Existing unrelated worktrees are
excluded. FULL_PATH applies. There is no architecture/provider change or new ADR.

The user's existing full approval covers disposable test infrastructure,
credential configuration, repairs, workflow dispatch, PR publication/merge and
VM shutdown after use. Commands still use the explicit live approval flag.
Secrets stay in qualified private Linux files and are never copied to evidence.
The WSL target owner is `tsw-test-incus-local`; Incus reports the existing
manager and two workers running. The protected runner is online and idle.
Native VM `TSW-RC1-Ubuntu` is off and must be requalified before native tests.

The baseline is not an accepted candidate: SonarCloud and hosted live run
34720815173 failed. Any product repair requires a new candidate and revalidation.
The hosted failure stopped at artifact readiness after mutation. A subsequent
read-only inspection observed all seven readiness probes ready; the prior
summary does not identify which probe failed. Preserve both observations.

## Distribution and locks

Real agents perform read-only parallel reviews:

- Faraday: candidate Sonar failure and minimal repair, issue #300.
- Poincare: workflow metadata and independent architecture/maintenance review.
- Laplace: acceptance sufficiency for R01/R03/R05/R07 and recovery runbook.

Codex owns integration, requirement reconciliation, live execution and cleanup.
Read-only streams do not modify shared files. All live operations are serialized.
Locks: both test targets, protected runner, candidate, registry, release matrix,
issue evidence and workflow metadata. Code repair streams require separate
branches/worktrees and declared disjoint paths before writing.

## Requirement matrix before execution

| Slice | Requirement | Verification needed | State |
|---|---|---|---|
| E00 | Resolve workflow metadata, candidate, applicability and targets | Independent review, source hashes, target qualification | IN_PROGRESS |
| E01 | WSL update, identity/data/config/credential preservation, repeat and recovery | Canonical update plus snapshots and authenticated acceptance | OPEN |
| E02 | Same update contract on native Linux; reconcile R02 | Qualified native run and historical applicability review | OPEN |
| E03 | WSL host restart, partial failure/recovery, authenticated acceptance | Actual host identity transition and failure/recovery observations | OPEN |
| E04 | Candidate-specific Sonar and container scan | Successful exact-revision external gate and scan output | FAILED_BASELINE |
| E05 | Hosted lifecycle and controlled stop | Exact revision/run/artifact audit and current failure resolution | OPEN |
| E06 | Qualified first-user walkthrough | Executed documented journey, resources, timing and acceptance | OPEN |
| E07 | Candidate image provenance and live admin/network boundaries | Digests, negative/positive access assertions and socket inspection | OPEN |
| E08 | Independent maintenance triage review | Architecture and test reviewers, tracked residuals | IN_PROGRESS |
| E09 | Complete row audit on final integrated SHA | Independent issue-completion review of all evidence | WAITING_DEPENDENCIES |

Historical issue closure and a green local gate are not live evidence. The six
issue evidence files will retain unverified states until the mapped assertions
have actually run. E09 alone owns the final release decision.

## Initial review and local verification

Poincare independently approved a read-only update runtime port and Incus adapter,
actual source/convergence checks and preservation of the original recovery plan.
Repeated recovery, mixed/stalled rollouts, unavailable runtime and no-op update
require regressions. Faraday identified Sonar S2083 at the private CA bundle copy;
Laplace identified that the old hosted suite contains 29 static and eight live
readiness tests, without full authenticated browser coverage. R05's old blanket
PASS is therefore insufficient for the stronger lifecycle requirements.

Three disjoint implementation streams were assigned isolated `/tmp` worktrees:
TLS source/test (E04), update ports/domain/adapter/composition/tests (E01), and
canonical runner/authentication summary/tests (E01). Shared documentation remains
owned by the integrator. Each stream commits only its own slice changes.

The ten unique slice metadata blocks parse, all dependencies resolve, owners are
roles, all context-pack governing hashes match and `git diff --check` passes.
For this workflow-metadata checkpoint the full runtime gate is deferred because
no Python or configuration behavior changed. Product-tree baseline hosted quality
run 34720675824 passed 2,004 tests (19 skips); this is local/CI evidence only.
Full quality is required again after consolidation of product repairs.

The authorized hosted retry 34721835136 failed at cluster swarm bootstrap. A
subsequent local canonical setup on the same product tree completed with exit 0.
The runner's failed-phase summary needs nested typed diagnostic details; neither
observation qualifies the missing candidate lifecycle assertions.
