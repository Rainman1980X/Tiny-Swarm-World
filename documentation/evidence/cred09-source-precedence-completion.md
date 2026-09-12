# CRED-09 source precedence completion evidence

Issue: [#296](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/296).
Tested candidate: `81443e80aad88cf4a9a647cb3241486f06c43e43`.
All four transition runs used clean checkouts of that candidate with the
`service-access` profile and explicit live consent. This record supersedes the
open source-precedence and consumer gaps in the
[2026-09-11 qualification record](credential-transition-verification.md).

Audit status: **PASS** (2026-09-12). Independent Product/Requirement Lead,
Senior System Architect and QA/issue-completion-auditor reviews approved all ten
stable requirements against candidate `81443e80`. No open acceptance gap remains.

## Root causes and bounded correction

The canonical parent contracts in
[#277](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/277) and
[#281](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/281) already
specify applicable secure provider > operator > default. The unconditional
rejection of distinct valid inputs contradicted that order. The resolver now
applies the specified precedence, retaining secure-source identification and
the self-hosted bootstrap prohibition.

A second defect discarded the completed post-bootstrap synchronization result
before Jenkins deployment. The application now reads that result once, just
before deploying Jenkins, and copies only `TSW_JENKINS_ADMIN_PASSWORD` into its
stack environment. Missing, blank, wrong-key or failed synchronization results
block consumption. Failed retries invalidate prior snapshots and public results.
The source label is recorded from the snapshot actually given to the runtime.

Only the supported Jenkins startup consumer in `service-access` receives this
binding. Other stacks, process environment and Infisical bootstrap inputs remain
outside this binding. This repairs the existing post-readiness consumer contract;
it adds no general rotation API, provider mode or persistent recovery mechanism.
See the [current source contract](../arc42/08_configuration/credential-source-precedence.md).

## Actual live results

| Host | Scenario | UTC run ID | Duration | Process exit | Result |
|---|---|---|---:|---:|---|
| WSL2 | Independent Vault-only change | `20260912T071242Z` | 140.439 s | 0 | LIVE_VERIFIED |
| WSL2 | Distinct operator/Vault conflict | `20260912T071614Z` | 138.717 s | 0 | LIVE_VERIFIED |
| Native Linux | Independent Vault-only change | `20260912T071903Z` | 63.548 s | 0 | LIVE_VERIFIED |
| Native Linux | Distinct operator/Vault conflict | `20260912T072101Z` | 63.631 s | 0 | LIVE_VERIFIED |

[The value-free JSON evidence](cred09-source-precedence-20260912.json) records
exact timestamps, commands with protected inputs redacted, candidate, profile,
per-operation observations, exit codes and protected report references. Its
runner digest identifies code only, never credential material. Original reports
remain under each host's protected `cred09-transitions/<run-id>/result.json`.

Every run verified:

1. Canonical readiness and a catalog-default baseline, with bootstrap source
   `default`, post-bootstrap consumed source `vault` and successful login.
2. A fresh authenticated cookie session established after baseline deployment.
3. In Vault-only cases, an independently changed Vault value with no explicit
   operator candidate for the tested key; in conflict cases, distinct nonempty
   operator and Vault values.
4. Actual Jenkins deployment evidence selecting `vault`, protected deployed-value
   equality with that selection and successful authentication using that value.
5. Rejection of the old/catalog credential with HTTP 401 and rejection of the
   non-effective operator/default input. The previous cookie became anonymous.
6. Only the Jenkins service specification and Jenkins Vault key changed.
7. Stable canonical reconcile, repeated deployment and a controlled replacement
   producing exactly one different Jenkins container.
8. Original login, Vault values and service specifications restored, the temporary
   value rejected, readiness successful and protected rotation records removed.

Source continuity combines actual consumed labels from deployment/redeployment
with protected runtime-value and service-specification comparisons. Bootstrap
labels alone are not treated as proof of runtime consumption. Only the intended
Jenkins `ForceUpdate` counter is excluded from restart/restoration comparisons.
Cookie evidence concerns credential update plus task replacement, not
password-only or global session revocation.

After restoration, the canonical post-install suite passed 37/37 with zero skips
on WSL2 (`20260912T071906Z`) and native Linux (`20260912T072311Z`). Each comprises
eight live HTTP/API/TLS checks and 29 static checks; neither is Selenium evidence.

## Requirement disposition

| Stable requirement | Implementation and verification | State |
|---|---|---|
| CRED-09-REQ-001 — sources/lifecycle | Canonical resolver and current contract; distinct-source, source-identity and bootstrap regressions | VERIFIED |
| CRED-09-REQ-002 — defaults/operator/secure on both hosts | Current catalog baselines and independent Vault cases; explicit distinct operator cases plus applicable historical matching-override results below | VERIFIED |
| CRED-09-REQ-003 — conflicting-source winner | Both conflict runs consumed Vault, authenticated it and rejected the distinct operator value | VERIFIED |
| CRED-09-REQ-004 — non-effective input/session semantics | HTTP 401 rejection and observed cookie invalidation in all four runs, with explicit session scope | VERIFIED |
| CRED-09-REQ-005 — rerun/restart comparisons | Reconcile, redeployment, exact task replacement, actual source provenance and protected value/specification equality in all runs | VERIFIED |
| CRED-09-REQ-006 — isolated intended transition | Only Jenkins service/key changed; unrelated Vault values and full service specifications compared | VERIFIED |
| CRED-09-REQ-007 — bootstrap/external guards | Resolver lifecycle/identity regressions and `test_infisical_provider_mode_rejects_unsupported_external_mixing`; guards retained | VERIFIED |
| CRED-09-REQ-008 — protected evidence | Values compared in memory or private rollback; published labels, booleans and operation outcomes only | VERIFIED |
| CRED-09-REQ-009 — restoration/cleanup | Four verified restorations, zero remaining rotation records on either host; deliberate retained migration recovery material | VERIFIED |
| CRED-09-REQ-010 — traceability/no blanket claims | This report, JSON evidence, historical records and explicit linked scope below | VERIFIED |

## Applicability, history and cleanup

Native matching-override run `20260911T214804Z` and WSL matching-override run
`20260911T215252Z` remain bounded historical results documented with their actual
candidate identities. They are reused as explicit matching-input acceptance,
not relabeled as executions of the new candidate. The current change repairs the
unequal-source and deferred-consumer paths; all four new runs exercise that
consumer, while current regressions retain matching-input and operator-fallback
coverage. This is the applicability reason for focusing new live execution on
the previously missing cases instead of repeating the same matching values.

Earlier failed attempts remain in the historical record. Their separately
verified rollback cleanup is preserved. Both manager nodes retain protected
migration archives and stopped source-volume keepers; these were not pruned or
published. The WSL temporary baseline environment was removed. The native
operator-owned baseline environment was deliberately retained. Both hosts have
zero remaining temporary CRED-09 rotation records.

Continuation links: [#285](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/285)
and [PR #293](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/pull/293).
The authenticated checks associated with
[#295](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/295), native
target work in [#298](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/298)
and lifecycle work in [#299](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/299)
provide shared-target/history context. This report does not close those issues
or claim blanket acceptance for #294 or #302.

## Local and external verification

`python3 tools/quality_gate.py quality` passed all six stages with exit 0:
1934 tests (18 skips), 18 architecture tests, three import contracts, lint,
verification policy and typecheck across 651 files. Focused changes passed 161
tests. The native target additionally passed 36 focused resolver/consumer/source
and unsupported-provider configuration checks. Skipped local cases are not
counted as live execution.

Candidate external checks passed:

- [Locked Python quality and coverage](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34680119061).
- [Conda Python 3.12 and 3.13](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34680119043).
- [SonarCloud analysis and quality gate](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34680259109).

Subsequent evidence-only commits do not change the tested product/test code;
publication review must verify that boundary. Native/WSL results do not qualify
untested external provider modes, other service rotations or power-loss recovery.
