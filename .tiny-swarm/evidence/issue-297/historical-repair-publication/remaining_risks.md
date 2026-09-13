# RC1-R01 Remaining Risks

Status: `INCOMPLETE`; no live acceptance or release decision is claimed.

- Complete WSL2/native A-to-B update, repeat no-op, failure/recovery and
  authenticated post-update acceptance remain open. First WSL update and
  continuity passed at `a2ff63fe`; the complete host scenario is `LIVE_PARTIAL`.
  Main owns execution and must finish target/evidence-path qualification.
- Main reports a healthy WSL authenticated baseline (25 tests, 9 routes,
  7 APIs), native SSH/Python 3.12 readiness, and a controlled Jenkins B image
  `jenkins:rc1-proof-b-20260913` with digest
  `sha256:54ae82f726498f62135ef367158ef30a46e757097ab4e8979586f71abc6e791c`.
  These are preparatory reports, not independently executed proof for this PR.
  Capture actual before/after immutable runtime identities: older 0.2.0 and
  0.3.0 tags resolved to identical content and cannot prove a changed image.
- The code permits identical-content tags. Live proof must deliberately use
  distinct safe content and demonstrate service/task convergence, preservation
  of node/service identities, persistent data and unrelated credentials/config.
- Recovery metadata retains image-transition intent; it neither backs up nor
  restores service data and does not reverse application data-format changes.
- Nonblocking boundary accepted in scoped review: a fresh forward update whose
  source has `rollback_completed` remains blocked even after recovery no-op.
- Nonblocking boundary accepted in scoped review: an already-target no-op does
  not load or validate recovery metadata; its `unchanged` evidence does not
  prove that stored recovery metadata is usable.
- Observation supports replicated services with positive replica counts;
  unsupported modes fail closed. Update/recovery overrides do not persist
  desired image configuration; operators must explicitly align later deployment
  intent. Current `platform reconcile` ensures nodes, not stack images.
- Full combined Python 3.12 passed at product-equivalent `a2ff63fe` (2,061 tests,
  18 skips). Published-head CI/Sonar results must still be observed separately. Local and historical checks do not constitute live/hosted success.
- #298/#299 own host evidence, #301 owns the protected runner chain, and #302
  owns the final audit under #294. #297's existing closed state is not acceptance.
- User authorization covers publishing this PR; **merge is held until main's
  live verification**. No issue closure or RC1 acceptance is requested.
