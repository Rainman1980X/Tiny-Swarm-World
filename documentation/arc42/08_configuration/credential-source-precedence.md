# Credential Source Precedence and Infisical Lifecycle

This is the CRED-03 source contract. The implementation is the domain-level
credential resolver; installers and synchronization adapters supply values but
do not implement a second precedence rule.

## Canonical precedence

For a credential that supports all listed sources in the applicable lifecycle
phase, the resolver applies this order:

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
catalog source; post-bootstrap Infisical values are kept when present. A
credential rotation is an explicit future operation and is not inferred from a
normal install rerun.

## Before/after drift evidence

Reconcile and restart checks may compare two in-memory resolution snapshots.
The comparison reports only the credential keys whose effective value or
source label changed, plus `values_equal` and `sources_equal` booleans. It does
not persist values, hashes, fingerprints, or provider responses. An unchanged
reconcile/restart must report both equality flags as true. A supported
transition is acceptable only when its intended service key is the sole
changed key and unrelated state remains healthy; live authentication and
cleanup evidence are still required to qualify the target.
