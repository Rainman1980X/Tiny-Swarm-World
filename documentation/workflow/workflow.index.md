# Workflow Index: RC1 Evidence Completion

Workflow id: `rc1-evidence-completion-20260912`
Authoring branch: `feature/workflow-rc1-evidence-20260912`
Planned execution branch: `feature/rc1-evidence-execution-20260912`
Execution profile: `FULL_PATH`
Status: `EXECUTION_IN_PROGRESS`

This indexed follow-up workflow creates the missing RC1 evidence for R01–R09. This index is explicitly selected for execution by `.codex/evidence/rc1-evidence-execution-20260913.md`. The existing Issue-252 workflow is retained as historical context.

## Requirement clarification gate

### Original Request

Create a workflow that produces every missing proof identified for RC1-R01 through RC1-R09: WSL2/native update evidence, WSL2 restart/recovery evidence, candidate Sonar and scan evidence, protected-runner reconciliation, final integrated audit, operator walkthrough, candidate image/security boundary evidence and independent maintenance review.

### Interpreted Intent

Create an executable, evidence-first workflow that turns each missing item into an owned slice with explicit prerequisites, live/external applicability, redaction rules, rollback/cleanup, verification commands and final issue-completion audit. R05 is verification-only because its hosted lifecycle and controlled fail-closed run already exist.

### Change Type

Release-evidence workflow authoring with live infrastructure, browser/API, external quality, security and documentation governance impact. No product behavior is changed by authoring this workflow.

### Affected Process Strand

RC1 requirement matrix -> Three-Amigos gate -> candidate freeze -> local gates -> serialized live/external evidence -> issue evidence packages -> independent reviews -> final RC1 decision.

### Affected Architecture Area

Canonical Python update and lifecycle runner, managed Incus/LXC provider, Docker Swarm target, WSL2/native Linux host boundaries, Classic acceptance tests, SonarCloud, Trivy, security evidence, operator documentation and RC1 release evidence.

### Explicit Requirements

- R01: verify live update and post-update acceptance on WSL2 and native Linux.
- R02: reconcile the historical native-Linux baseline and its applicability to the final candidate.
- R03: verify WSL2 restart, partial-failure recovery and authenticated acceptance afterward.
- R04: observe a candidate-specific SonarCloud gate and execute the required container scan.
- R05: preserve and reference the already verified successful and fail-closed hosted runs.
- R06: freeze the final integrated SHA and audit every RC1 evidence row.
- R07: execute the documented first-user journey on a qualified target with timing/resource evidence.
- R08: capture candidate image digests and verify live admin/network/socket boundaries.
- R09: record an independent architecture/test review of the maintenance triage.
- Keep all evidence redacted, checksummed where required and truthful under the verification-state policy.
- Do not mark an issue `DONE` while any applicable requirement is open or unverified.

### Implicit Requirements

- Live validation is serialized because targets, candidate state, evidence roots and release documents are shared.
- WSL2 and native Linux are separate evidence profiles; one cannot substitute for the other.
- Missing, queued, skipped, cancelled, blocked or unavailable checks are non-success states.
- The native Linux VM remains stopped unless the assigned slice explicitly requires it and an approved target is selected.
- No live mutation occurs during authoring; execution requires explicit operator consent and qualified targets.
- Existing Issue-252 assets are retained; execution explicitly selects this index and its issue-local metadata.

### Assumptions

- The current `main` commit at authoring is the candidate baseline until RC1-E00 freezes a later exact SHA.
- The protected runner and disposable Incus/LXC test target used by R05 remain available for evidence inspection or explicitly requalified.
- The project-provided live runner and existing acceptance tests are canonical.
- The user’s previously granted approval covers the controlled live-validation path, but each execution still records per-invocation consent.

### Non-Goals

- No new deployment architecture, provider, service split, React frontend, Java/Maven/Spring structure or Windows-native project behavior.
- No automatic secret provisioning, password rotation or storage of user-provided credentials.
- No release publication, tag creation or branch-protection change.
- No conversion of historical or local evidence into live/external success.
- No speculative refactor for R09 follow-up issue #329.

### Risks

- Live mutation can leave partial state; each slice needs an owned cleanup and retained diagnostics path.
- Candidate drift between host runs can invalidate otherwise green evidence; RC1-E00 freezes the SHA.
- SonarCloud, Trivy, registry or runner unavailability must remain explicit non-success states.
- Browser/API evidence can leak credentials; only redacted summaries and checksums are retained.
- Shared release files create merge conflicts; all final matrix edits are serialized in RC1-E09.

### Open Questions

None block authoring. Execution must resolve target-specific facts in RC1-E00: target owner, host classification, resource contract, exact update transition, restart ownership, image digest source, evidence root and available external credentials.

### Blocking Questions

None for workflow creation. A missing execution prerequisite blocks the affected slice and is recorded as `LIVE_PREREQUISITE_MISSING`, `LIVE_CONSENT_MISSING` or `EXTERNAL_GATE_UNAVAILABLE`.

### Confidence and Decision

Confidence: 93 percent.

Decision: `READY_FOR_WORKFLOW`.

The request, affected issues, evidence outputs, role ownership, dependency graph, quality commands and stop conditions are explicit. Runtime facts remain execution-time prerequisites rather than authoring guesses.

## Target picture

```text
RC1-E00 candidate freeze and Three Amigos
  -> R01 WSL2 update + native-Linux update
  -> R03 WSL2 failure/restart/recovery
  -> R04 Sonar + container scan
  -> R05 existing hosted evidence reconciliation
  -> R07 first-user walkthrough
  -> R08 candidate digest + live security boundaries
  -> R09 independent maintenance review
  -> R06 final row-by-row audit and RC1 decision
```

## Ordered slices and dependency graph

| Slice | Owner issue | Result | Dependencies | Execution state |
|---|---:|---|---|---|
| RC1-E00 | #298 / all | Candidate freeze, applicability, Three-Amigos decision and target qualification | none | serial prerequisite |
| RC1-E01 | #297 | WSL2 update and post-update acceptance | E00 | serialized live |
| RC1-E02 | #297 | Native-Linux update and post-update acceptance | E00,E01 | serialized live |
| RC1-E03 | #299 | WSL2 restart, partial failure, recovery and authenticated acceptance | E01 | serialized live |
| RC1-E04 | #300 | Candidate SonarCloud and container scan evidence | E00 | serialized external/security |
| RC1-E05 | #301 | Existing protected runner evidence reconciliation | E00 | read-only evidence |
| RC1-E06 | #308 | Qualified first-user walkthrough and resource/timing evidence | E01,E02,E03 | serialized live |
| RC1-E07 | #309 | Candidate image digests and live admin/network boundaries | E00,E04 | serialized live/security |
| RC1-E08 | #310 | Independent maintenance triage architecture/test review | E00 | review |
| RC1-E09 | #302 | Final integrated SHA, row-by-row audit and exact RC1 decision | E01,E02,E03,E04,E05,E06,E07,E08 | final serial audit |

Execution mode is serial at the workflow level because live targets, release evidence and candidate provenance are shared. S3D may split a slice into disjoint review streams only when its locks permit it.

## Role ownership

- Senior Workflow Architect: workflow integrity, slice ordering and execution handoff.
- Senior Requirement Engineer: requirement matrices, issue drift and acceptance traceability.
- Senior System Architect: hexagonal boundaries, provider model, restart/recovery and architecture review.
- Senior Python Automation Developer: canonical runner, CLI/update contracts and focused repairs.
- Senior Tester: local regression, acceptance, failure propagation and evidence completeness.
- Senior DevOps Engineer: WSL2/native Linux, Incus/LXC, Docker/Swarm, runner and cleanup operations.
- Live Evidence Validation Expert: live states, redaction, checksums and artifact retention.
- Senior Security Sandbox Engineer: credentials, image provenance, sockets, admin and network boundaries.
- Senior Documentation Engineer: operator docs, release matrix and Arc42 synchronization.
- Release Baseline Governance Expert: final candidate and RC1 decision review.
- Issue Completion Auditor: final PASS/INCOMPLETE/BLOCKED/REJECTED decision for each issue.

No frontend React role is applicable.

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


## Documentation synchronization

- Update the issue evidence package after every slice.
- Update `documentation/release/rc1-candidate-evidence.md` with exact candidate provenance.
- Update `documentation/release/rc1-decision.md` only in RC1-E09 after all prerequisite rows are reviewed.
- Keep `documentation/arc42/11_risks_and_debt.adoc` aligned with the workflow and the actual remaining evidence risks.
- Preserve historical evidence and distinguish it from candidate-specific evidence.

## Commit and publication plan

Workflow authoring is published only from `feature/workflow-rc1-evidence-20260912` with a guarded documentation commit and push to `origin/feature/workflow-rc1-evidence-20260912`. It must not merge a PR, delete branches, execute live infrastructure or promote the indexed workflow automatically. Later execution uses one commit per slice and the normal issue/PR lifecycle.

## Arc42 check status

`CHECKED_UPDATED`: the RC1 evidence follow-up and its shared live/external risks are recorded in `documentation/arc42/11_risks_and_debt.adoc`.

## Handoff to workflow execute

1. Promote the intended issue-local workflow path or explicitly extend the executor to select the indexed workflow.
2. Run S3/S3D preflight and create distribution evidence for RC1-E00.
3. Execute slices in topological order, keeping live validation serialized.
4. Run the Issue Completion Auditor for every issue before any final closure claim.
5. Let RC1-E09 publish exactly one allowed RC1 decision based on observed evidence.

## Included issue workflows

- [RC1-R01 — Canonical Classic update live evidence](issues/issue-297/workflow.md): `RC1-E01`, dependencies `RC1-E00`.
- [RC1-R02 — Native-Linux baseline applicability](issues/issue-298/workflow.md): `RC1-E00`, dependencies `none`.
- [RC1-R03 — WSL2 restart and failure recovery evidence](issues/issue-299/workflow.md): `RC1-E03`, dependencies `RC1-E01`.
- [RC1-R04 — Candidate SonarCloud and container scan evidence](issues/issue-300/workflow.md): `RC1-E04`, dependencies `RC1-E00`.
- [RC1-R05 — Protected runner evidence reconciliation](issues/issue-301/workflow.md): `RC1-E05`, dependencies `RC1-E00`.
- [RC1-R06 — Final integrated RC1 evidence audit](issues/issue-302/workflow.md): `RC1-E09`, dependencies `RC1-E01, RC1-E02, RC1-E03, RC1-E04, RC1-E05, RC1-E06, RC1-E07, RC1-E08`.
- [RC1-R07 — Qualified first-user operator journey](issues/issue-308/workflow.md): `RC1-E06`, dependencies `RC1-E01, RC1-E02, RC1-E03`.
- [RC1-R08 — Candidate image and live security boundaries](issues/issue-309/workflow.md): `RC1-E07`, dependencies `RC1-E00, RC1-E04`.
- [RC1-R09 — Independent maintenance triage review](issues/issue-310/workflow.md): `RC1-E08`, dependencies `RC1-E00`.

Excluded issues: none. RC1-R02 is included as a historical-baseline applicability slice because R01 and R06 must distinguish historical from candidate-specific native-Linux evidence.

## Execution qualification

See `.codex/evidence/rc1-evidence-execution-20260913.md`. E00 records the product baseline and repair scopes. Final candidate freeze follows those repairs; no failing baseline is accepted. E02 metadata is in `issues/issue-297/workflow-native.md`. Evidence-only commits after a freeze must identify their product-tree equivalence; final external checks still bind the integrated revision.
