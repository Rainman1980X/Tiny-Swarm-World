# WSL2 Service Authentication Evidence: #285 / CRED-07

Date: 2026-09-03. Host class: WSL2. Source checkout: `/mnt/d`.

The supported authentication paths were executed after the protected fresh
install `20260903T072101Z`. Each credential was resolved in process from the
immutable internal-test catalog. Values, tokens, response bodies and headers
were not printed or persisted.

| Service | Supported path | Observed result |
|---|---|---|
| Portainer | `POST /api/auth`, admin user, JWT presence | PASS |
| Infisical | `POST /api/v3/auth/login`, access-token presence | PASS |
| Nexus | `GET /service/rest/v1/security/users` with basic auth | PASS, HTTP 200 |
| Jenkins | `GET /whoAmI/api/json` with basic auth on port 11080 | PARTIAL: HTTP 200 observed; authenticated identity not recorded |
| SonarQube | `GET /api/authentication/validate`, JSON `valid=true` | PASS |
| Pulsar | `GET /admin/v2/clusters` with catalog bearer token | PASS, HTTP 200 and standalone cluster |
| Pulsar Manager | CSRF acquisition followed by `POST /pulsar-manager/login` | PASS, login success |

The successful installer deployment phase independently completed the Portainer
admin-access, Infisical bootstrap/consumption, Nexus admin-access, SonarQube
admin-access and Pulsar Manager bootstrap steps. This file supplies the
redacted direct authentication trace that the phase summary does not print.

This is WSL2/default-catalog evidence only. Native-Linux parity and a supported
custom/Infisical override remain open.

The 2026-09-09 independent recheck identified that Jenkins can return HTTP 200
for an anonymous identity. The historical status therefore does not establish
authentication. A new authorized check must inspect `authenticated=true` and
the expected identity, or prove an unequivocally authorized operation, in
memory and persist only the redacted outcome.
