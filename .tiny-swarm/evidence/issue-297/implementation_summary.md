# RC1-R01 Implementation Summary

Status: `INCOMPLETE` — R01 repair assembled for review; candidate-specific
WSL2/native update, preservation, recovery and authenticated acceptance remain
open. This package maps to #297 under #294 and does not close either issue.

## Publication provenance

Date: 2026-09-13. Branch: `fix/rc1-r01-pr-20260913`.
Base: `1bac487e6ca1e86b1df6d813ed58037b1cbe253a` (`origin/main`).
Product tip before this evidence-only commit:
`f92d6b28f37ef086f4bc657de8939e4e4222d3f0`.

Only the four R01 repair commits selected by the integration owner were cherry-picked, without conflicts:

| Original | Publication equivalent | Purpose |
|---|---|---|
| `7083e1f7` | `981905a9` | Require complete authenticated canonical runner evidence. |
| `ca71a3d6` | `d6689974` | Observe runtime convergence and preserve original recovery state. |
| `524e7c4f` | `7ef1d152` | Clarify source/operator update semantics in the existing ADR and usage section. |
| `a6baac14` | `f92d6b28` | Resolve the three independent recovery/parser review findings. |

The authoring commit `e320179f` is not an ancestor. Product, test, runner,
configuration and CI files match execution commit
`a2ff63fe6597fe41a1fcb4102b41efcea247602d` exactly. The execution worktree was
read only during assembly; no authoring workflow files enter this PR.

## Implemented behavior

Preview checks references and configured stack/service membership without
runtime observation. Actual apply requires consent and reads service/task
image references, states and rollout through an application port backed by
the existing Incus manager subprocess route. Success requires actual target
convergence; an already converged target is a verified no-op. Old/mixed tasks,
failed rollouts and unavailable/malformed observations cannot establish success.

Recovery retains the original plan across retries and failures. Completed
automatic rollback counts as a recovery no-op only when the requested original
target actually converges; forward failure detection remains intact. Stored
plan fields and `recorded_at` must be nonempty strings; unknown current or
desired Docker task states fail before historical filtering. Metadata is
persisted atomically and is not a service-data backup.

The canonical lifecycle runner requires readiness and authenticated acceptance
after its phases, validates terminal structured evidence and expected counts,
propagates failures, and uses private per-operation evidence directories.
Static runner tests are not a successful hosted or cross-host run.

The user previously authorized test operations, publication and merge. The
integration owner holds this PR until live verification and required checks
are complete. No live commands were executed while assembling the PR.
