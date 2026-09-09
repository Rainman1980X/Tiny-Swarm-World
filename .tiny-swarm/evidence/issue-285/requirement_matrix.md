# Requirement Matrix: #285 / CRED-07

Statuses are evidence states, not predictions. `VERIFIED` is limited to the
observed WSL2/default-catalog scope where the requirement permits that scope;
`PARTIAL` records WSL2 evidence with an unverified native-Linux counterpart.
The issue remains blocked while any required live scope is open.

| ID | Requirement | Type | Evidence | Status |
|---|---|---|---|---|
| CRED-07-REQ-001 | WSL2 checkout under `/mnt/<drive>` is exercised with a fresh install. | live | Protected run `20260903T072101Z`, reset/setup both 0 | VERIFIED |
| CRED-07-REQ-002 | WSL2 standard internal-test path is supported. | live | Default source labels and completed setup | VERIFIED |
| CRED-07-REQ-003 | Native Linux fresh install is exercised. | live | Native VM technically supported, but current host RAM cannot fit canonical guest resources plus host reserve | BLOCKED |
| CRED-07-REQ-004 | Portainer login succeeds in each applicable environment. | live/auth | `service_authentication.md` direct WSL2 auth plus deployment access; native target absent | PARTIAL |
| CRED-07-REQ-005 | Infisical bootstrap/login succeeds in each applicable environment. | live/auth | `service_authentication.md` direct WSL2 auth plus bootstrap/consumption; native target absent | PARTIAL |
| CRED-07-REQ-006 | Other catalog human-facing services are checked where feasible. | live/auth | Authorized WSL2 API/browser acceptance, including Jenkins authenticated identity; native counterpart unverified | PARTIAL |
| CRED-07-REQ-007 | Post-install service/UI/API acceptance is recorded. | live | `service_authentication.md` and endpoint matrix below | PARTIAL |
| CRED-07-REQ-008 | Rerun/reconcile does not cause credential drift. | live | Run `20260909T051827Z`: before/after values and source metadata equal, five services authenticate both times; native counterpart open | PARTIAL |
| CRED-07-REQ-009 | Environment recreation resolves deterministic defaults again. | live | WSL2 fresh reset recreated all-default source metadata | PARTIAL |
| CRED-07-REQ-010 | A supported custom or Infisical override replaces the default. | live/auth | Run `override-20260909T052321Z`: operator/Infisical override deployed, admin identity confirmed, default HTTP 401, restoration verified | VERIFIED |
| CRED-07-REQ-011 | Restart/recovery relevant to credential consumption is exercised. | live | Run `20260909T051827Z`: Portainer forced restart exit 0 and subsequent JWT authentication; native counterpart open | PARTIAL |
| CRED-07-REQ-012 | Update is tested only if a canonical update workflow exists. | applicability | No canonical `update` workflow exists; `reconcile` remains distinct | NOT_APPLICABLE |
| CRED-07-REQ-013 | Evidence contains no raw passwords, tokens, or authorization headers. | security | Protected-root redaction scan PASS; installer output prints labels only | VERIFIED |
| CRED-07-REQ-014 | Blocked/skipped/degraded scenarios are never reported as PASS. | governance | Earlier failures and missing targets retain explicit non-pass states | VERIFIED |
| CRED-07-REQ-015 | Full local quality gate is green on the final candidate. | local | Browser-storage repair: `python3 tools/quality_gate.py quality`, 1913 tests, 18 skips, OK; `test_results.md` | VERIFIED |
| CRED-07-REQ-016 | Final acceptance matrix maps every parent EPIC criterion to evidence. | governance | Matrix records authorized WSL2 evidence; native parity remains open, matching override does not isolate Vault-only precedence | BLOCKED |
| CRED-07-REQ-017 | Three-Amigos WSL2 fresh-install scenario is observed. | live | Protected WSL2 run completed all configured phases | VERIFIED |
| CRED-07-REQ-018 | Three-Amigos native-Linux parity scenario is observed. | live | No native-Linux target | BLOCKED |
| CRED-07-REQ-019 | Three-Amigos rerun scenario is observed. | live | WSL2 reconcile plus source/value comparison and reauthentication passed; native counterpart open | PARTIAL |
| CRED-07-REQ-020 | Three-Amigos override scenario is observed. | live | Protected Jenkins override accepted and prior default rejected with HTTP 401; restoration verified | VERIFIED |

## WSL2 service/API acceptance

Observed after the protected successful run; status codes are recorded without
response bodies or credentials:

| Surface | Result |
|---|---|
| Portainer `/api/status` | HTTP 200 |
| Infisical `/` | HTTP 200 |
| SonarQube `/api/system/status` | HTTP 200 |
| Nexus UI `/` | HTTP 200 |
| Nexus registry `/v2/` | HTTP 401 (auth boundary) |
| Jenkins `/` | HTTP 200 |
| Pulsar Admin API `/admin/v2/clusters` | HTTP 401 (auth boundary) |
| Pulsar Manager `/` | HTTP 200 |
| Swagger UI `/` | HTTP 200 |
| Swagger editor `/` | HTTP 302 |
| Service Access `/` | HTTP 200 |

## Parent EPIC #277 traceability

| Parent criterion from #277 | Evidence mapping | Status |
|---|---|---|
| Canonical `TSW1234STW5678` default | Immutable catalog, all-default source metadata, WSL2 setup | PARTIAL |
| Universal default for technically compatible human-facing services | Catalog plus WSL2 service access | PARTIAL |
| Centralized deterministic alternatives for incompatible components | Catalog derivations plus WSL2 completed deployment | PARTIAL |
| Machine/bootstrap credentials need no manual preparation | WSL2 fresh install with no override file | PARTIAL |
| Special-format values satisfy consumers | WSL2 Pulsar/Traefik/Infisical/SonarQube phases completed | PARTIAL |
| Random default-password generation absent from normal path | CRED-04 implementation and all-default WSL2 source metadata | PARTIAL |
| Random-default recovery persistence absent from normal path | CRED-04 implementation and WSL2 run | PARTIAL |
| Reinstall/reconcile is deterministic | WSL2 source/value equality and reauthentication proved; native open | PARTIAL |
| Fresh checkout installs without a password file | WSL2 standard path used catalog defaults | PARTIAL |
| WSL2 `/mnt/d` is not blocked by unnecessary credential-state permissions | Protected-root WSL2 run and reset/setup success | VERIFIED |
| Native Linux has equivalent behavior | No native-Linux target | BLOCKED |
| Infisical override can replace defaults | Matching Infisical/operator Jenkins override deployed and authenticated; isolated vault-only live precedence not proved | PARTIAL |
| Explicit operator overrides are supported | Protected 0600 input resolved as operator source and deployed successfully | VERIFIED |
| Self-hosted Infisical has no circular bootstrap dependency | WSL2 bootstrap, sync and consumption phases completed | PARTIAL |
| Documentation marks defaults `INTERNAL/TEST ONLY` | CRED-06 docs and installer output | VERIFIED |
| Enterprise AD/LDAP/SSO/network/IAM boundary is external | CRED-06 documentation | VERIFIED |
| Installer output provides URL/login information | WSL2 output contains URLs/users and no values | VERIFIED |
| Obsolete modes/files/abstractions are removed or isolated | CRED-04/CRED-06 plus WSL2 normal path | VERIFIED |
| Unit/integration tests cover resolution and precedence | Full local quality gate | VERIFIED |
| Live/E2E default logins succeed | `service_authentication.md` plus deployment access steps; native absent | PARTIAL |
| Live/E2E override succeeds | Jenkins identity verified with override; default HTTP 401; restoration passed | VERIFIED |
| Architecture/configuration documentation matches behavior | Catalog, compose, installer, tests and WSL2 run | PARTIAL |
