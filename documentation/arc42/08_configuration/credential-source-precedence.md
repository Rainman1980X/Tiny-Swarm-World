# Credential Source Precedence and Infisical Lifecycle

This is the CRED-03 source contract. The implementation is the domain-level
credential resolver; installers and synchronization adapters supply values but
do not implement a second precedence rule.

## Canonical precedence

For a credential that supports these sources in the applicable lifecycle phase,
valid distinct values follow one deterministic precedence order. A lower-priority
operator value does not invalidate an applicable secure value:

1. an applicable secure provider value (`vault`);
2. an explicit operator value (`operator`), from the process environment or an
   approved local override file;
3. the deterministic CRED-01 internal-test catalog value (`default`).

The resolver returns the selected value to the caller and exposes only the
source label in evidence. Valid labels are `default`, `operator`, and `vault`.
Raw values, tokens, environment-file contents, and authorization material are
never evidence. A bootstrap-only consumer cannot use a post-bootstrap vault
value retroactively; such a value is applicable to synchronization or a
consumer that is explicitly rebuilt after readiness.

## Lifecycle phases

| Phase | Secure source allowed | Fallback | Rule |
|---|---|---|---|
| `bootstrap` | An explicitly identified, already available external secure source only | operator, then catalog default | Self-hosted Infisical is not queried because it is the service being started. |
| `post-bootstrap` | Ready self-hosted Infisical or another explicitly identified secure source | operator, then catalog default | Existing Infisical values may win and are reported as `vault`; synchronization is a separate post-bootstrap step. |

The current service-access workflow supports `self_hosted` Infisical. Setting
`TSW_INFISICAL_PROVIDER_MODE=external` is rejected as unsupported by this
self-hosted workflow, so an external endpoint cannot accidentally be treated as
the local bootstrap target. A future external integration must add an adapter,
readiness contract, and isolated deployment path before enabling that mode.

## Bootstrap sequence

```text
operator environment/files -> resolver (bootstrap) -> self-hosted Infisical
                                                     |
                                                     v
                            ready Infisical -> resolver (post-bootstrap) -> sync/evidence
```

The self-hosted instance receives its encryption, authentication, database,
admin identity, and other startup inputs before its own readiness check. It does
not read those inputs from itself. After readiness, the sync step may read an
existing managed value and keep it as the secure source; a missing value is
written from the bootstrap resolution.

## Installer contract

The normal installer has one credential path: deterministic catalog defaults
plus explicit operator overrides, with a ready secure provider consulted only
in its applicable post-bootstrap phase. Secret-source mode selection and
generated/fixed/recovery credential files are not supported. Unsupported
combinations fail closed with source names and lifecycle phase, never with raw
values.

## Reruns and synchronization

Reruns are idempotent. Bootstrap inputs are reused from the same operator or
catalog source; post-bootstrap Infisical values are kept when present. A general
credential rotation API is not provided. The Jenkins consumer described below
reapplies an explicitly changed selected value during deployment; unchanged
inputs do not generate a new value.

## Before/after drift evidence

Reconcile and restart checks may compare two in-memory resolution snapshots.
The comparison reports only the credential keys whose effective value or
source label changed, plus `values_equal` and `sources_equal` booleans. It does
not persist values, hashes, fingerprints, or provider responses. An unchanged
reconcile/restart must report both equality flags as true. A supported
transition is acceptable only when its intended service key is the sole
changed key and unrelated state remains healthy; live authentication and
cleanup evidence are still required to qualify the target.

## Post-bootstrap Jenkins consumption

In the `service-access` profile, Infisical readiness and complete synchronization
precede Jenkins deployment. Synchronization retains an in-memory resolution
snapshot only after every manifest entry succeeds. A failed initial sync or
failed rerun makes that snapshot unavailable.

Immediately before Jenkins deployment, the application reads that completed
snapshot once and overlays only `TSW_JENKINS_ADMIN_PASSWORD` into a copy of the
Jenkins stack environment. It does not alter process environment, bootstrap
inputs or other stack consumers. Missing, blank or unexpected selected keys
block deployment. The recorded consumed snapshot is published only after the
runtime deployment command succeeds, and is cleared before each attempt.

The Jenkins deployment verification exposes the actual consumed source label
as `resolved_sources`; it does not expose the value or a fingerprint. Live
qualification must additionally compare the protected runtime value and perform
real authentication. Secret-reference consumption checks alone do not prove
that a selected value reached a running service.

This implements the existing CRED-03 post-readiness consumer contract for the
Jenkins startup password. It does not claim independent Vault-driven rotation
for databases, Infisical's own bootstrap material, or every service.

## Live transition qualification

The opt-in runner `tests/e2e/classic/run_credential_transition_live.py` supports
`--scenario matching-override`, `--scenario vault-only`, and
`--scenario conflicting-sources`. Each requires `--approve-live` and a protected
`--env-file` on an authorized healthy target with its named Jenkins home already
migrated. A Vault-only case uses catalog bootstrap fallback with no explicit
operator candidate for the tested key; only Vault is deliberately changed. The
conflicting case uses different nonempty operator and Vault values. Both must
prove that Vault is actually consumed and authenticates while non-effective
inputs are rejected.

The runner also checks canonical readiness, baseline, redeployment, reconcile,
controlled task replacement, unrelated service/Vault equality and restoration.
Cookie behavior is scoped to credential update plus task replacement; it is not
a password-only revocation guarantee. Historical failed runs and their cleanup
remain evidence and are not retroactively relabeled.
