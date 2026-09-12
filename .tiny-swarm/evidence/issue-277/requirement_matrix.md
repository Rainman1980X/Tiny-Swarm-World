# EPIC #277 requirement matrix

Source: complete GitHub #277 read on 2026-09-12. E02-01 through E02-22
map in order to the unchanged 22 acceptance criteria; E02-23/24 capture
scenarios/Definition of Done and E02-25 the parent completion discipline.

Preflight: clean main `9b3b172060ac945ae4759614078851171de6533b`; dedicated
`docs/epic-02-completion-audit-20260912` branch. Documentation-only audit; the
active #252 workflow is not executed. Allowed files: this parent evidence
directory. Existing implementation stream worktree is retained untouched.
No new infrastructure mutation or executable change.

Sibling evidence references below are relative to `.tiny-swarm/evidence/`;
documentation/test references are repository-relative.

| ID | Requirement | Implementation | Verification | State |
|---|---|---|---|---|
| E02-01 | Canonical internal-test default password | CRED-01 catalog constant | issue-279/requirement_matrix.md: CRED-01-REQ-003; catalog tests | VERIFIED |
| E02-02 | Human-facing components use the universal default when supported | CRED-01 compatible definitions | issue-279/requirement_matrix.md: CRED-01-REQ-003/012; CRED-08 four live phases | VERIFIED |
| E02-03 | Incompatible components have centralized documented deterministic alternatives | CRED-01 catalog constraints and derivations | issue-279/requirement_matrix.md: CRED-01-REQ-004/013; catalog format tests | VERIFIED |
| E02-04 | Machine/bootstrap values require no manual preparation | CRED-02 canonical resolver and CRED-04 standard-path cleanup | issue-280/requirement_matrix.md: CRED-02-REQ-001/004/005; native all-default install record below | VERIFIED |
| E02-05 | Special-format cryptographic values satisfy consumer requirements | CRED-01 key/token/encoding/htpasswd definitions | issue-279/requirement_matrix.md: CRED-01-REQ-002/004; format tests and later live acceptance | VERIFIED |
| E02-06 | Unneeded random default generation removed from standard path | CRED-04 deleted generators | issue-282/deleted-path-inventory.md; issue-282/requirement_matrix.md | VERIFIED |
| E02-07 | Random-default recovery/persistence removed from standard path | CRED-04 deleted generated snapshots/recovery helpers | issue-282/deleted-path-inventory.md; stateless resolver regression | VERIFIED |
| E02-08 | Reinstall/reconcile resolves the same defaults deterministically | CRED-02 stateless catalog; CRED-09 actual value/source comparisons | issue-280/requirement_matrix.md: CRED-02-REQ-007; issue-285 live reconcile; issue-296 final transition comparisons | VERIFIED |
| E02-09 | Fresh checkout installs without first creating a password file | CRED-02/04 default path requires no ordinary password input file | tests.test_simple_installer stateless/no-file regressions; historical WSL fresh install; native all-default install context | VERIFIED |
| E02-10 | WSL2 /mnt/d is not blocked by unnecessary credential-state permissions | CRED-05 protected runtime storage and no generated-default state | issue-285/test_results.md WSL installation; issue-295 storage qualification and runner regressions | VERIFIED |
| E02-11 | Native Linux has equivalent credential behavior | Same canonical installer/catalog on qualified native host | Native install context below; issue-296 four transition runs; issue-295 both-host browser/API reports | VERIFIED |
| E02-12 | Supported Infisical overrides replace defaults | CRED-03 contract, corrected CRED-09 precedence/deferred Jenkins consumer | issue-296/completion_audit.md; native/WSL Vault-only and conflict reports | VERIFIED |
| E02-13 | Explicit operator overrides supported where appropriate | Canonical resolver operator fallback and supported input contract | credential resolution tests; issue-296 historical matching-override acceptance and final conflict rejection | VERIFIED |
| E02-14 | Self-hosted Infisical has no circular bootstrap dependency | Local default resolution precedes post-readiness synchronization | issue-281/completion_audit.md; issue-296 bootstrap/provider regressions; default-source native installation | VERIFIED |
| E02-15 | Documentation marks defaults INTERNAL/TEST ONLY | CRED-01 catalog and CRED-06 operator guidance | issue-279/requirement_matrix.md: CRED-01-REQ-006/009; issue-284 completion audit | VERIFIED |
| E02-16 | AD/LDAP/SSO/network/IAM remain external enterprise concerns | CRED-06 handbook/configuration boundary | issue-284/requirement_matrix.md: CRED-06-REQ-006 | VERIFIED |
| E02-17 | Installer output provides immediately usable URLs/login convention | CRED-06 safe console output | issue-284/requirement_matrix.md: CRED-06-REQ-002/003/009; output regressions | VERIFIED |
| E02-18 | Obsolete modes/files/abstractions removed or isolated behind supported use | CRED-04 deletion and explicit post-bootstrap/override boundaries | issue-282/deleted-path-inventory.md and architecture-before-after.md | VERIFIED |
| E02-19 | Unit/integration coverage verifies deterministic resolution and precedence | Catalog/resolver/installer regression suites | Current focused command in test_results.md; CRED-09 161 focused and full-gate evidence | VERIFIED |
| E02-20 | Live/E2E verifies UI logins with internal-test defaults | CRED-08 real Firefox invalid/valid flows and protected APIs | issue-295/live_results_20260912.json: four clean final phases, six UI logins per phase | VERIFIED |
| E02-21 | Live/E2E verifies configured overrides | CRED-09 supported Jenkins runtime transitions | issue-296/completion_audit.md; credential-transition-verification.md and cred09-source-precedence-completion.md | VERIFIED |
| E02-22 | Architecture/configuration docs match implementation | CRED-01/03/04/06 and corrected CRED-09 source contract | issue-282/architecture-before-after.md; issue-284 audit; documentation/arc42/08_configuration/credential-source-precedence.md | VERIFIED |
| E02-23 | All six Three-Amigos scenarios and desired clone/install/login flow satisfied | Rows 01-22 jointly cover fresh/recreated/component-specific/stronger/enterprise/WSL scenarios | Child scenario matrices, historical installations, current resolver tests and CRED-08/09 affected-path reruns | VERIFIED |
| E02-24 | Definition of Done: deterministic model is actual standard path, not extra legacy mode | CRED-02 routing plus CRED-04 removal, CRED-06 docs and CRED-08/09 acceptance | Child implementation/audit chain; historical applicability in implementation_summary.md; independent parent review | VERIFIED |
| E02-25 | Preserve historical limits and complete independent parent evidence audit | Parent synthesis; no blanket main/native/RC1 claim from old runs | Six parent files and completion_audit.md; original child failed/partial results unchanged | VERIFIED |
