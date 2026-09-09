# WSL2 secure live path

This is the canonical path strategy for issue #271 and for any authorized
mutating RC1 run from a WSL2 checkout under `/mnt/<drive>`.

## Boundary

The source checkout may remain on `/mnt/*` so that source traceability and the
tested commit are preserved. A Windows-mounted source tree is not a valid
mutable secret store. `chmod 600` reported on DrvFS does not establish the
POSIX ownership and permission semantics required by this project.

Mutable live credentials and live evidence must be stored on a WSL-native Linux
filesystem. The operator-owned environment file must be a regular file owned
by the effective user, mode `0600`, in an owner-only directory mode `0700`.
The evidence root must be created and verified with mode `0700`; its parent
must be user-owned and not group- or world-writable.

## Operator preparation

From the WSL shell, create the secure location and populate it with the
operator's already-rotated credentials using a secure editor or secret manager:

```bash
install -d -m 700 "$HOME/.local/state/tiny-swarm-world"
export TSW_INSTALL_ENV_FILE="$HOME/.local/state/tiny-swarm-world/live-installation.env"
${EDITOR:-vi} "$TSW_INSTALL_ENV_FILE"
chmod 600 "$TSW_INSTALL_ENV_FILE"
```

Do not copy the repository-local environment file from `/mnt/*`, print it,
paste it into evidence, or place its values in a command line. Set
`TSW_INSTALL_ENV_FILE` explicitly for each live run.

Run the non-mutating live diagnostics first:

```bash
python3 tools/install_debugger.py --live --env-file "$TSW_INSTALL_ENV_FILE"
```

The debugger distinguishes source-tree classification from secure secret and
evidence storage. It fails closed when the configured secret file is missing,
not native, not user-owned, not `0600`, or is in a directory that is not
`0700`. No command output or environment value is persisted by the live
runner.

## Authorized run contract

Before any mutation, the operator must rotate or revoke the credential exposed
by the earlier failed attempt. Supply only a non-secret ticket or change
reference, never the credential itself:

```bash
python3 tools/live/run_classic_acceptance.py \
  --approve-live \
  --env-file "$TSW_INSTALL_ENV_FILE" \
  --credential-rotation-reference "ticket-271-YYYYMMDD"
```

The runner writes redacted metadata and checksum files to a WSL-native state
root (or the explicitly configured `TSW_LIVE_EVIDENCE_ROOT`, which is the
exact evidence-root path). It records only
whether the rotation reference was supplied. It records source and storage
classifications, owner/mode verification, commit, host metadata, operation
labels, exit codes, policy states and redaction confirmation; it never writes
secret values, full environments, authorization headers, raw stdout/stderr or
private keys.

The source override `--allow-wsl-windows-filesystem` is used internally only to
permit the already-qualified `/mnt/*` source tree. It does not bypass secret
storage qualification. Blocked, skipped, partial or degraded operations never
produce `LIVE_VERIFIED`.

The protected CI workflow expects repository or environment variables for the
native env-file path, native evidence-root path, target-owner reference, and
credential-rotation reference. Its qualification step rejects missing values
before checking the live runner and uploads only the configured evidence root.

## Evidence and completion

Both Classic browser suites qualify a shared Linux-native evidence directory
before live access. `TSW_LIVE_EVIDENCE_ROOT` selects the exact root;
`TSW_CLASSIC_EVIDENCE_ROOT` remains a fallback when that variable is unset.
Without either override, browser evidence uses
`${XDG_STATE_HOME:-$HOME/.local/state}/tiny-swarm-world/evidence/classic-public-beta-rc1`.
Existing directories must already be user-owned mode `0700`; Windows-mounted
or otherwise unqualified storage fails closed. Post-install summaries use
private run subdirectories. Default local checks still isolate missing-consent
records from live results and do not constitute browser acceptance.

The live bundle must be reviewed under the
[live green-path evidence contract](live-greenpath-evidence-contract.md).
Fresh Install, post-install acceptance, Reconcile and Update are separate
live requirements. Local tests prove path policy and redaction behavior only;
they do not substitute for an authorized WSL2 lifecycle result.
