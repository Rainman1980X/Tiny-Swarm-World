# RC1-R03 WSL2 Lifecycle Scenario Matrix

The protected runner must execute these phases in order against one declared
clean target and one candidate SHA:

| Phase | Required observation | Failure behavior |
|---|---|---|
| Diagnostics | Host class, source/evidence storage and prerequisites | Stop before mutation |
| Fresh setup | Fresh managed installation completes | Stop and retain redacted terminal evidence |
| Fresh acceptance | Authenticated service/browser/API checks pass | Stop before reconcile |
| Reconcile | Desired state converges without reset | Stop before post-reconcile acceptance |
| Reconcile acceptance | Authenticated checks remain valid; credentials and routes do not drift | Stop before update |
| Update | Selected service moves from declared source image to target image | Stop before post-update acceptance |
| Update acceptance | Updated service and dependent routes remain authenticated and ready | Stop before recovery |
| Recovery | Persisted rollback state reverses the selected update | Stop if source state does not match |
| Recovery acceptance | Services remain usable after recovery | Retain state and diagnostics |
| Restart boundary | Qualified WSL2 restart restores node identity, Swarm, routes and readiness | Non-pass; no inferred success |

`classic_e2e`, `reconcile_e2e`, `update_e2e` and `recovery_e2e` use the same
assertion-heavy test discovery command. A service restart is not evidence of
the host restart boundary. Native-Linux parity is consumed from RC1-R02.
