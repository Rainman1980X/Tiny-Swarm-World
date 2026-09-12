# CRED-09 credential transition verification

> Historical checkpoint from 2026-09-11. Its PARTIAL/BLOCKED statements describe
> the candidate tested then. Current source-precedence completion is documented
> in [the 2026-09-12 report](cred09-source-precedence-completion.md).

This record concerns [issue #296](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/296),
following [#277](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/277),
[#285](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/285) and
[PR #293](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/pull/293).
The user explicitly authorized live tests and publication on 2026-09-11.
At that checkpoint, the issue remained **PARTIAL**; the unsupported cases below are not passes.

## Executed scope

The opt-in runner `tests/e2e/classic/run_credential_transition_live.py` exercises
the existing Jenkins startup override with a matching Infisical value. It uses
the canonical resolver, CLI deployment and reconcile operations. It does not
introduce a rotation API. The target must already have a healthy installation,
protected environment file and migrated named Jenkins home.

The successful native run `20260911T214804Z` and WSL run
`20260911T215252Z` both verified:

- The explicit operator value selected `operator`; only the Jenkins key changed.
- An existing Vault value selected `vault` and authenticated. This was an
  existing-value read/use check, not independent changed-Vault propagation.
- Distinct operator/Vault values were rejected before mutation.
- Deployment applied the new Jenkins credential; the new login authenticated,
  the old Basic credential returned 401, and the previously authenticated cookie
  became anonymous (HTTP 200) across credential update and task replacement.
- Only the Jenkins service specification and Jenkins Vault key changed.
- Reconcile preserved service specifications, Vault values and source labels.
- Controlled restart produced exactly one different Jenkins container; login,
  Vault values, source labels and service specifications remained valid.
- Restoration recovered the original login and Vault values, rejected the
  temporary credential and restored service specifications. Only Jenkins's
  intentional `ForceUpdate` restart counter is excluded from restart/restore
  comparisons. The temporary rollback file was removed.

The subsequent native protected post-install suite `20260911T214920Z` passed
37/37, with eight live HTTP/API/TLS checks, 29 static checks and zero skips.
The restored WSL post-install run `20260911T215454Z` also passed 37/37
(eight live, 29 static), with zero skips. Its temporary baseline environment
file was removed after verification. This is not Selenium evidence. The separate full native reboot evidence is in
[the cold-start recovery record](native-linux-cold-start-recovery.md).

Protected value-free run reports are retained under each host's
`~/.local/state/tiny-swarm-world/evidence/cred09-transitions/`. The reports bind
the tested candidate commit, dirty-tree state and runner-file digest. The
native run preceded the final additional preflight mount guard; local guard
regressions and the WSL run cover that addition. Digests identify code only;
credential fingerprints are never emitted.

## Failed attempts and recovery

Earlier failures remain evidence and are not relabeled as successful runs:

| Host/run | Result and subsequent action |
|---|---|
| Native `20260911T214118Z` | Session preflight failed before mutation. Initial login-page request and form submission were corrected. |
| Native `20260911T214236Z` | The CLI launcher lacked execute permission. Vault restoration completed; services were not changed. |
| Native `20260911T214545Z` | System Python lacked project dependencies. Vault and authentication were restored; services were unchanged. The runner now invokes the canonical CLI with its own Python interpreter. |
| Native `20260911T214629Z` | Transition, reconcile and restart passed; strict restoration comparison failed because canonical compose added the Jenkins mount's stack namespace label after the earlier manual migration. Credentials were restored. |
| WSL `20260911T215056Z` | Transition, reconcile and restart passed; strict restoration comparison failed because canonical compose removed an empty mount `DriverConfig` added by the manual migration. Credentials were restored. |

The canonical compose results established the baselines for subsequent runs.
The runner's comparison was not weakened to hide these changes. The three
native protected rollback records were removed only after a separate check
confirmed original credential inputs, Jenkins Vault value, authentication and
service equivalence apart from the documented mount label and restart counter.
The unsuccessful generic cleanup comparison against all catalog values was
retained separately; missing/unmanaged Vault entries cannot be assumed to
equal catalog values. The final cleanup uses original run inputs and the
successful restoration evidence. The WSL failed-run rollback record was likewise
removed after original-input, Vault and authentication checks plus service
equality excluding only the documented empty `DriverConfig` and restart counter.

## WSL migration prerequisite

Before transition tests, the existing WSL anonymous Jenkins home was migrated
under the [migration safeguards](../user_guide/jenkins-home-migration.md).
There were zero configured jobs and zero busy executors. Protected archives,
the original service specification and a stopped source-volume keeper remain
on the manager node under recovery run `20260911T214929Z`.

All 1275 copied entries matched content, ownership, modes and symlinks. The
pause lasted 8.96 seconds. After cutover, all 1168 regular files in the retained
source still matched the archive. Authentication succeeded and quiet mode was
cancelled. The named home is reused by subsequent credential task replacements;
this does not recover historical jobs or prove untested historical data.

## Open issue requirements

- The current resolver rejects distinct nonempty operator and Vault values.
  Issue #296 asks for an authenticated winner for that case. Negative conflict
  tests cannot satisfy this incompatible acceptance requirement. A contract
  decision remains necessary; this test task does not change the resolver.
- Post-bootstrap Vault-only selection does not rebuild a running bootstrap
  consumer. Independently changing only Vault and proving service uptake remains
  unsupported and unverified.
- Cookie behavior was observed across credential update plus task replacement,
  not password-only session revocation. The evidence applies to Jenkins, not
  automatic rotation across every service.
- External CI/SonarQube status is separate from local and live acceptance.

The independent completion review accepts the bounded evidence but does not
authorize marking #296 done, merging the PR or closing the issue.

## Requirement disposition

| Requirement | Evidence and remaining scope | State |
|---|---|---|
| 001 — sources and lifecycle | Canonical precedence documentation and resolver regressions | LOCAL_VERIFIED |
| 002 — default/operator/secure cases on both hosts | Baselines and matching Jenkins transitions verified; independent changed-Vault uptake absent | PARTIAL |
| 003 — conflicting-source winner | Actual resolver rejects distinct values before selection | BLOCKED_CONTRACT_CONFLICT |
| 004 — non-effective credentials/session behavior | Old Basic credential rejected and old cookie invalidated across task replacement on both hosts; no password-only guarantee | LIVE_VERIFIED, bounded |
| 005 — reconcile/restart state | Value/source and service comparisons passed for matching overrides on both hosts | LIVE_VERIFIED, bounded |
| 006 — only intended transition changes | Only Jenkins service and Jenkins Vault key changed on both hosts | LIVE_VERIFIED, bounded |
| 007 — noncircular bootstrap/external-mode rejection | Existing phase guards and local regression coverage | LOCAL_VERIFIED |
| 008 — protected comparisons | Values remain in memory or protected rollback records; public outcomes contain no credentials/fingerprints | VERIFIED |
| 009 — restoration and cleanup | Original credential restored; temporary overrides and rollback inputs removed; migration backups deliberately retained | LIVE_VERIFIED |
| 010 — traceability and honest status | Linked issues/PR and retained failed attempts in this record | VERIFIED |

## Local publication checks

`python3 tools/quality_gate.py quality` completed with exit 0: verification
policy, lint, three import contracts, 18 architecture tests, typecheck across
651 files and 1927 tests (18 skips). The focused runner-safety and compose
repository tests passed 61/61. Skipped opt-in cases are not claimed as executed
by the local gate; live results above are separate executed evidence.

## CI host-isolation correction

The prior-head GitHub locked and Conda quality jobs all failed the same routing
evidence test: a native CI host stopped at the new kernel prerequisite before
reaching the intended evidence-write failure. The failure was reproduced with
a mocked native host lacking prerequisites. The regression now exercises native
Linux and WSL explicitly with mocked host readiness, verifies the native guard
is called, and still requires evidence failure before any stack step. No
production prerequisite is bypassed. The focused host-isolation and guard tests
passed; final full quality was rerun after this test-only correction.
