# Parent verification evidence

## Directly inspected native installation source

On 2026-09-12 root reconnected to the existing qualified native Hyper-V VM through
Windows PowerShell OpenSSH with its previously trusted host key. Read-only Python
inspection selected non-secret fields from the protected directory
`~/.local/state/tiny-swarm-world/evidence/installation-tests/native_linux/20260911T084338Z`.
No reset, install, reconcile or restart was repeated for this audit.

| Field | Observed value |
|---|---|
| git_head | 87fff38 (resolved in repository to 87fff38ee6761d474e222e0c535f5622da98021d) |
| started_utc | 2026-09-11T08:43:38Z |
| finished_utc | 2026-09-11T09:18:00Z |
| host_runtime_type | native_linux |
| service_profile | service-access |
| fresh_install_reset | required |
| reset-run.exit / context reset_exit | 0 / 0 |
| setup-run.exit / context setup_exit | 0 / 0 |
| credential_sources | all 16 catalog inputs report default |

Source files: context.txt, reset-run.exit, setup-run.exit. Raw setup/reset logs,
credentials, private paths, connection strings and environment contents are not
published. The SSH session was closed after inspection. Historical no-op reconcile
and 37/37 before/after manager restart are recorded in
[the native continuation](../issue-296/history-before-completion/CRED-09B-native-linux-live.md).
That 37-test suite contains eight live HTTP/API/TLS plus 29 static checks, not
37 Selenium logins. Current UI proof comes from CRED-08.

## Reused executed evidence

- CRED-01/02/03/04/06 child matrices/audits establish catalog format, stateless
  defaults, cleanup, bootstrap sequencing, overrides and documentation. The
  requirement matrix identifies the exact child requirement/test per parent row.
- [WSL installation and reconcile](../issue-285/test_results.md) plus
  [redacted results](../issue-285/live_results_20260909.json) retain original
  revisions and bounded outcomes.
- [CRED-09 audit](../issue-296/completion_audit.md) and
  [source-precedence completion](../../../documentation/evidence/cred09-source-precedence-completion.md)
  establish both-host supported overrides/reconcile/replacement/restoration.
- [CRED-08 audit](../issue-295/completion_audit.md) and
  [twelve component reports](../issue-295/live_results_20260912.json) establish
  both-host baseline/post-restart browser/API acceptance. Four final phases have
  nine browser routes, six actual UI logins and seven authenticated API checks
  each, no skipped live checks; eight canonical checks pass before and after.
- CRED-08 full local gate at d254b769: 1,974 tests, 18 local skips, 18 architecture
  tests, three import contracts, 655 typed files; six stages PASS. Independent
  focused rerun: 58 PASS. These are reused executed checks, not newly run here.
- PR #312 final head37747919: Python quality, Conda3.12/3.13 and SonarCloud PASS;
  merge9b3b1720 changes no tested executable content beyond that verified head.

## Current audit-only verification

The documentation gate is `git diff --check`. No full local gate or live run is
repeated for this parent synthesis because it changes no executable/configuration
or quality policy; QUALITY.md permits this documented narrower gate. Targeted
catalog/resolver/installer tests and evidence-link/matrix checks were executed
as recorded below. Publication CI is separate and must be checked on its actual head.

Executed on the unchanged main executable tree9b3b1720 while preparing this audit:

```bash
PYTHONPATH=src python3 -m unittest tests.domain.configuration.test_internal_test_credentials tests.domain.configuration.test_credential_resolution tests.test_simple_installer
git diff --check
```

Results: 47 tests PASS (exit0); whitespace check PASS. A read-only validation
confirmed all25 requirement rows and every relative evidence link resolve.
