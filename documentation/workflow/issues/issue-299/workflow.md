# Workflow Slice RC1-E03: WSL2 restart and failure recovery evidence

Workflow id: `rc1-evidence-completion-20260912`
Issue: #299
Issue code: `R03`
Source: https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/299
Authoring branch: `feature/workflow-rc1-evidence-20260912`
Planned execution branch: `feature/rc1-evidence-execution-20260912`
Status: `READY_FOR_WORKFLOW_EXECUTION`

## Purpose

Exercise WSL2 partial failure, managed service recovery, restart resilience and authenticated acceptance after restart.

## Prerequisites

- RC1-E00 candidate freeze and Three-Amigos decision, unless this is RC1-E00.
- Qualified target and explicit live/external consent for applicable gates.
- Current issue evidence directory with the six mandatory files.
- Exact candidate SHA and redacted evidence root.
- No unrelated uncommitted changes in the execution worktree.

## Scope

- Requirement mapping: R03-02, R03-03, R03-04, R03-05, R03-06, R03-07, R03-08
- Affected files: tools/live/run_classic_acceptance.py, .tiny-swarm/evidence/issue-299/, documentation/evidence/
- Affected modules: WSL2 lifecycle, failure/recovery orchestration, authenticated acceptance
- Affected contracts: phase stop-on-failure, persisted rollback state, restart readiness, redacted evidence
- Dependencies: RC1-E01

## Non-goals

- No unrelated product refactor or provider change.
- No secrets in Git, logs or evidence.
- No release acceptance claim from local-only, historical, skipped or unavailable checks.
- No direct execution from a shared branch or the existing active Issue-252 workflow branch.

## Slice metadata

```yaml
slice_id: RC1-E03
profile: FULL_PATH
owner: senior-devops
secondary_reviewers: [senior-requirement-engineer, senior-system-architect, senior-python-automation-developer, senior-tester]
affected_files: [tools/live/run_classic_acceptance.py, .tiny-swarm/evidence/issue-299/, documentation/evidence/]
affected_modules: [WSL2 lifecycle, failure/recovery orchestration, authenticated acceptance]
affected_contracts: [phase stop-on-failure, persisted rollback state, restart readiness, redacted evidence]
dependencies: [RC1-E01]
parallel_group: rc1-evidence-serial
file_locks: [issue-evidence, release-evidence]
contract_locks: [verification-state, redaction, candidate-provenance]
architecture_locks: [linux-wsl2-only, incus-lxc-provider, docker-swarm-first, hexagonal-boundaries]
quality_gates:
  targeted: [git diff --check]
  required: [python3 tools/quality_gate.py quality]
documentation:
  arc42: documentation/arc42/11_risks_and_debt.adoc
  adr: none
stop_conditions: [restart ownership is unclear, partial state has no cleanup path, authentication evidence cannot be redacted, required phase is skipped]
```

## Architecture and execution constraints

- Preserve the Python hexagonal architecture and the Linux/WSL2-only product model.
- Use managed Incus/LXC for the supported node-provider path; Multipass is forbidden.
- Keep orchestration in existing tools and application ports; do not move shell, filesystem, Docker or provider details into domain code.
- Reuse the canonical Classic runner and assertion-heavy tests. Do not create a second live-test framework.
- Live commands are opt-in, require explicit per-invocation consent, use an owned target and write only redacted evidence.
- The native Linux target is used only when required by the slice; the native Linux VM stays stopped when it is not needed.
- No credentials, tokens, cookies, private keys, full environment files or raw command output may enter the repository or evidence.

## Python Automation Assessment

The workflow primarily consumes existing Python automation and evidence contracts. Product code may change for an observed live defect, failing external analysis or reproduced acceptance-contract defect, with focused regression coverage and independent review. The canonical commands are inspected before execution; no shell behavior is duplicated in workflow YAML.

## Frontend Assessment

No React or browser frontend module is in scope. Browser/API acceptance uses the existing Classic tests and records redacted observed results only.

## Test Strategy

Run the nearest targeted checks before each live or external slice, then run the required full gate before the final audit:

```bash
git diff --check
python3 tools/quality_gate.py lint
python3 tools/quality_gate.py arch-tests
python3 tools/quality_gate.py typecheck
python3 tools/quality_gate.py test
python3 tools/quality_gate.py quality
```

The full local gate remains local evidence. Live, browser and SonarCloud states use `documentation/process/verification-state-policy.md`.

## Resilience and evidence requirements

Every live slice records the exact candidate SHA, host/profile, target owner, scenario, start/end or duration, exit code, readiness before/after, cleanup/recovery outcome and redacted artifact references. Failed required phases stop dependent mutation. A blocked, queued, skipped, cancelled, unavailable or partial result cannot become a pass.

## Issue Completion Discipline

- Requirement matrix path: `.tiny-swarm/evidence/issue-<number>/requirement_matrix.md`
- Required evidence path: `.tiny-swarm/evidence/issue-<number>/`
- Required evidence files: `requirement_matrix.md`, `implementation_summary.md`, `changed_files.md`, `test_results.md`, `remaining_risks.md`, `acceptance_checklist.md`
- Requirement Lead review: required before slice completion
- System Architect Reviewer review: required before slice completion
- Test / Evidence Reviewer review: required before slice completion
- Issue Completion Auditor review: required before any `DONE` or issue-close claim
- DONE blocking rule: any open, blocked, partial, degraded, skipped, failed-to-verify or unredacted requirement forces `INCOMPLETE`, `BLOCKED` or `FAILED`.

## Automatic Work Distribution Policy

`workflow execute` automatically analyzes this slice for separable backend, frontend, tests, runtime, documentation, quality, architecture and security streams. Real Codex subagents are used where supported; otherwise an explicit role-based fallback review is recorded. `.codex/evidence/slice-<number>-distribution.md` is required before implementation and `.codex/evidence/slice-<number>-consolidation.md` is required after implementation. Codex remains final integration owner.

Parallelization is forbidden for overlapping files, shared release matrices, generated evidence, unclear architecture, mandatory ordering, shared migrations, uncertain secrets, or weakened safety guards.

## Git Worktree Execution Rule

Every executable slice uses a dedicated worktree. Parallel streams use branches named `<workflow-branch>-slice-<number>-<stream>`. Stream workers must not merge directly to the workflow branch. Codex consolidates after evidence and tests pass.

## Parallel Execution

- Can this workflow run in parallel? Only static reviews with disjoint evidence paths may be parallelized after S3D approval.
- Conflicting workflows: the existing Issue-252 RC1 remediation workflow and any live deployment/reset workflow.
- Shared files: `documentation/release/**`, `.tiny-swarm/evidence/**`, `tools/live/**`, active workflow metadata.
- Shared infrastructure: qualified WSL2/native-Linux targets, protected runner, Incus/LXC, Docker/Swarm, SonarCloud and registry.
- Requires isolated worktree: yes.
- Requires serialized live validation: yes.
- Merge-order constraints: E00, host live slices, external/security slices, R09 review, then E09 final audit.

## Stop conditions

Stop and classify through the Typed Error Router when branch, target ownership, consent, evidence root, redaction, rollback, candidate SHA, required tool, external result or architecture ownership is unclear. Stop after any post-mutation failure until cleanup and retained diagnostics are complete.

## Definition of Done

The issue-local slice is complete only when its requirement matrix has no open requirements, its six mandatory evidence files exist and are consistent, relevant local gates pass, applicable live/external results are `LIVE_VERIFIED`/`EXTERNAL_GATE_VERIFIED`, and the Issue Completion Auditor records `PASS`. The final workflow is complete only when RC1-E09 has reconciled every row and published one allowed RC1 decision.

## Handoff to workflow execute

Run S3/S3D preflight, promote this indexed workflow to the active workflow path or explicitly select its issue-local path, create distribution evidence, execute the dependency graph in order, record consolidation evidence, and stop before any release claim when a required row is not verified.


## Requirement-to-verification mapping

The implementation must update the issue matrix so every mapped requirement has implementation evidence and at least one relevant test, static check, live result or external result. The following mapping is the minimum required scope: `R03-02, R03-03, R03-04, R03-05, R03-06, R03-07, R03-08`.

## Documentation and evidence outputs

- `.tiny-swarm/evidence/issue-299/requirement_matrix.md`
- `.tiny-swarm/evidence/issue-299/implementation_summary.md`
- `.tiny-swarm/evidence/issue-299/changed_files.md`
- `.tiny-swarm/evidence/issue-299/test_results.md`
- `.tiny-swarm/evidence/issue-299/remaining_risks.md`
- `.tiny-swarm/evidence/issue-299/acceptance_checklist.md`
- `.codex/evidence/slice-<number>-distribution.md`
- `.codex/evidence/slice-<number>-consolidation.md`

## Definition of Done for this slice

The slice is complete only when all mapped requirements are verified, the issue evidence package is consistent, the applicable live/external state is observed and redacted, and the Issue Completion Auditor records `PASS`. For RC1-E05, existing run and artifact inspection is sufficient and no new live mutation is permitted.

## Handoff

After this slice, update the indexed workflow ledger and continue only to the declared dependent slices. RC1-E09 is the sole owner of the final RC1 decision document.
