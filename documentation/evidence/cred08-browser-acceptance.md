# CRED-08 browser and authenticated acceptance

Issue [#295](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/295).
Both-host baseline and post-restart acceptance: LIVE_VERIFIED at
`d254b76980a344a67295d8395e61002bf0730b0c`; independent completion audit PASS
([review](../../.tiny-swarm/evidence/issue-295/completion_audit.md)).
See [executed results](../../.tiny-swarm/evidence/issue-295/test_results.md) and
[per-route/task evidence](../../.tiny-swarm/evidence/issue-295/live_results_20260912.json).

Membership comes from the active effective access model's `service_access_links`;
credential metadata determines authentication applicability. Unknown credential
routes fail closed. The current `service-access` profile produces this inventory:

| Route | UI | Expected principal / protected operation | Failure signal |
|---|---|---|---|
| Infisical | Actual login form; fresh session after rejected attempt | Configured login email; token-authorized organization read | HTTP 400 exact invalid-login message or 401/403; wrong UI credentials |
| Jenkins | Actual login; same-session whoAmI | admin; authenticated=true and matching name | 401/403; anonymous HTTP 200 insufficient |
| Nexus | Sign-in modal; fresh session | admin supplied; protected security/users read containing expected account (not a current-user API) | 401/403; explicit incorrect-credential UI response |
| Portainer | Actual login; fresh session | admin; token-authorized users/me matches Username | 422 exact Invalid credentials or 401/403 |
| Pulsar admin API | Route navigation; no login form | configured superuser token; nonempty cluster-list read | invalid Bearer token rejected with 401/403 |
| Pulsar Manager | Actual login; fresh session | admin; login response principal plus protected environments read | exact error response or 401/403 |
| SonarQube | Actual login; same-session current user | configured username; isLoggedIn=true and matching login | 401/403; public project navigation insufficient |
| Service Access | Route navigation | No login required by effective model | navigation failure |
| Swagger | Route navigation | No login required by effective model | navigation failure |

One invalid attempt per browser/API check is followed by a fresh valid session.
No transport failure is counted as API rejection. The browser and API criteria
must both pass. The API evidence calls this `authenticated_access_verified`:
Nexus, Infisical and Pulsar prove a protected operation, not an identity endpoint.
Credentials come from the existing canonical input contract without fallback
identities. Bootstrap source labels are not proof of post-bootstrap Vault usage;
that separate provenance remains bounded to #296's recorded transition evidence.

Run inside Linux/WSL, from a clean candidate checkout with installed test/browser
dependencies and the existing TLS trust bundle:

```bash
PYTHONPATH=src python3 -m tests.e2e.classic.run_authenticated_acceptance_live \
  --approve-live --phase baseline
```

An operator input file can be selected with `--env-file /protected/operator.env`;
the runner qualifies it before loading it and binds both canonical environment
source selectors. Evidence-root precedence remains `TSW_LIVE_EVIDENCE_ROOT`,
`TSW_CLASSIC_EVIDENCE_ROOT`, then the protected XDG/home state directory. Each
invocation creates a unique private phase directory. No screenshots, traces or
raw runner output are retained. A dirty checkout, skipped test, empty inventory,
missing credential or failed authenticated operation cannot be LIVE_VERIFIED.

After an independently approved controlled restart, repeat with
`--phase post-restart`. That phase label alone proves no restart: pair it with
recorded before/after task IDs, unchanged persistent mounts/service settings,
restart commands, timestamps, readiness and recovery/cleanup. This issue uses
the existing #298 native target and #299 lifecycle boundary; it does not provision
another VM or qualify database/power-loss/full-host recovery.

## Historical evidence mapping

- [#285 / PR #293 evidence](../../.tiny-swarm/evidence/issue-285/live_results_20260909.json)
  remains historical at `7380f7519eeb05ed49bc5006422895eeebbb20a5`. Its browser
  markers did not enforce the strengthened current assertions; affected UI
  acceptance must be rerun, not relabeled as current success.
- [#296 source precedence](cred09-source-precedence-completion.md) is bounded to
  `81443e80aad88cf4a9a647cb3241486f06c43e43`, with both-host Jenkins transition,
  rejection and task-replacement evidence. Its 37/37 post-install runs contain
  eight HTTP/API/TLS and 29 static checks; they are explicitly not Selenium.
- [Native host recovery](../../.tiny-swarm/evidence/native-cold-start-recovery/post-repair-host-reboot-20260911.md)
  remains a historical whole-host recovery result, not current browser acceptance.

Current requirement matrix, checks, remaining risks and independent audit live
under `.tiny-swarm/evidence/issue-295/`. #294/#302 and #308 may consume only the
bounded actual results, never a blanket release claim.
