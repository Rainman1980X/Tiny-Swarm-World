# RC1-R01 Acceptance Checklist

Status: `INCOMPLETE`. Local repair readiness is separate from #297/#294
acceptance; the historical completion audit remains incomplete.

- [x] New isolated branch starts at current `origin/main`; only the four named
  R01 commits were cherry-picked, without authoring ancestry or workflow edits.
- [x] Accepted update/reconcile architecture is retained and operator semantics
  distinguish static preview, runtime apply, recovery metadata and data backup.
- [x] Canonical CLI, consent, unsupported transitions and static preview have
  local regression coverage.
- [x] Runtime source and task-image/state convergence, no-op behavior and
  failed/mixed/paused rollouts have local regression coverage.
- [x] Original recovery state survives repeats/failures; the three independent
  rollback/schema/task-state findings are covered and resolved locally.
- [x] Canonical runner requires complete readiness/authentication evidence and
  fails closed on incomplete summaries, skips or nonzero exits in local tests.
- [x] Combined scoped update/runner suite passes: 99 tests, zero skips.
- [x] Publication static architecture/lint/typecheck and final text checks pass.
- [x] Main records full Python 3.12 at product-equivalent `a2ff63fe`: 2,061
  tests, 18 skips; retained log inspected.
- [x] First WSL distinct-image update and continuity pass at `a2ff63fe`; this
  is partial evidence and does not satisfy complete host acceptance below.
- [ ] WSL2 actual distinct-image update, repeat/recovery, preservation and
  authenticated post-update service/browser/API acceptance are `LIVE_VERIFIED`.
- [ ] Equivalent native-Linux scenario is `LIVE_VERIFIED`.
- [ ] Protected Nightly/host lifecycle consumption is verified on the candidate.
- [ ] Redacted evidence records exact tested SHA, host/profile, before/after
  immutable task images, commands, timing, exit codes and recovery outcome.
- [ ] Published-head required CI/Sonar results are observed and satisfactory.
- [ ] Independent final completion audit verifies all issue requirements.
- [ ] Main authorizes merge after live verification; no merge is performed by
  this publication task.
