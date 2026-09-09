# Canonical `internal-test` Credential Catalog

Status: implemented catalog contract for Classic/internal-test, issue #279

## Safety boundary

Every value in this catalog is explicitly `INTERNAL/TEST ONLY`. The values are
deterministic so that disposable local acceptance fixtures can be reproduced
without a credential file or live secret-management service. They are public
test material, have intentionally low secret entropy, and must never be used
for production, a shared environment, or an operator's real local deployment.
Production and normal local operation must use operator-owned or externally
managed credentials and must follow
[`secret-handling-policy.md`](../../security/secret-handling-policy.md).

The single authoritative implementation is
`src/tiny_swarm_world/domain/configuration/internal_test_credentials.py`.
Consumers resolve values through `internal_test_credential(key)` or
`internal_test_credentials()`; they do not maintain another internal-test
default list. The catalog is the only default source for the normal installer;
operator overrides and ready secure-provider values are handled by the
centralized lifecycle resolver.

## Active Classic inventory

The table records the current repository contract from the setup manifest,
configuration contract, and active Compose assets. `Required` describes the
current Classic/internal-test setup contract; `Active` distinguishes a
currently wired consumer from a reserved manifest entry.

| Key | Owner | Consumer | Type | Required | Active | Deterministic value or derivation | Technical constraint |
|---|---|---|---|---:|---:|---|---|
| `TSW_PORTAINER_ADMIN_PASSWORD` | Portainer service administrator | Portainer admin API and first-run admin bootstrap | `human_password` | yes | yes | `TSW1234STW5678` | 12–128 printable ASCII characters; first-run bootstrap and subsequent admin API use. |
| `TSW_NEXUS_ADMIN_PASSWORD` | Nexus service administrator | Nexus admin API after `/nexus-data/admin.password` bootstrap | `human_password` | yes | yes | `TSW1234STW5678` | 12–128 printable ASCII characters; bootstrap replacement then API reuse. |
| `TSW_JENKINS_ADMIN_PASSWORD` | Jenkins service administrator | Jenkins Configuration as Code admin user | `human_password` | yes | yes | `TSW1234STW5678` | 12–128 printable ASCII characters; read at controller startup through JCasC. |
| `TSW_SONARQUBE_ADMIN_PASSWORD` | SonarQube service administrator | SonarQube admin API | `human_password` | yes | yes | `TSW1234STW5678!a` | 12–128 printable ASCII characters, at least one lowercase character, and at least one `!@#$%^&*()_+`; enforced before deployment. |
| `TSW_POSTGRES_PASSWORD` | SonarQube PostgreSQL service owner | SonarQube PostgreSQL container and JDBC connection | `machine_password` | yes | yes | `TSW1234STW5678` | 12–128 alphanumeric ASCII characters safe in the PostgreSQL connection value; initialized on a new data directory and reused. |
| `TSW_SONARQUBE_POSTGRES_PASSWORD` | SonarQube PostgreSQL service owner | SonarQube JDBC password and PostgreSQL container | `machine_password` | yes | yes | `TSW1234STW5678` | Same PostgreSQL contract; Compose falls back to `TSW_POSTGRES_PASSWORD` when this alias is absent. |
| `TSW_PULSAR_TOKEN_SECRET_KEY` | Pulsar service administrator | Pulsar standalone broker token authentication | `signing_key` | yes | yes | `Base64(SHA-256(UTF-8(TSW1234STW5678:pulsar)))` | Standard Base64 ASCII, 44 characters, decodes to exactly 32 bytes/256 output bits; consumed through `data:;base64`. |
| `TSW_PULSAR_ADMIN_TOKEN` | Pulsar service administrator | Pulsar Admin API bearer authentication and healthcheck | `token` | yes | yes | Deterministic JWT `sub=admin`, HS256, signed by the catalog signing key | Three Base64url JWT segments; HMAC-SHA256 signature must verify with `TSW_PULSAR_TOKEN_SECRET_KEY`; no time claim keeps tests deterministic. |
| `TSW_PULSAR_MANAGER_ADMIN_PASSWORD` | Pulsar Manager service administrator | Pulsar Manager bootstrap API and UI admin login | `human_password` | yes | yes | `TSW1234STW5678` | 12–128 printable ASCII characters; bootstrap creates or verifies the UI admin user. |
| `TSW_INFISICAL_LOGIN_EMAIL` | Infisical service administrator | Infisical initial bootstrap admin and CLI login | `username/email` | yes | yes | `admin@tiny-swarm-world.local` | ASCII email syntax, 3–254 characters; consumed for initial bootstrap and later identity login. |
| `TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD` | Infisical service administrator | Infisical initial bootstrap admin | `human_password` | yes | yes | `TSW1234STW5678` | 12–128 printable ASCII characters; consumed during initial bootstrap and CLI login. |
| `TSW_INFISICAL_ENCRYPTION_KEY` | Infisical service administrator | Infisical `ENCRYPTION_KEY` setting | `encryption_key` | yes | yes | First 32 hex characters of `SHA-256(UTF-8(TSW1234STW5678:infisical-encryption))` | Lowercase hex ASCII; exactly 32 characters/16 decoded bytes; changing it invalidates encrypted material. |
| `TSW_INFISICAL_AUTH_SECRET` | Infisical service administrator | Infisical `AUTH_SECRET` setting | `signing_key` | yes | yes | Lowercase hex `SHA-256(UTF-8(TSW1234STW5678:infisical-auth))` | Exactly 64 hex characters/32 decoded bytes; read before authentication and used to sign auth material. |
| `TSW_INFISICAL_POSTGRES_PASSWORD` | Infisical PostgreSQL service owner | Infisical PostgreSQL container and `DB_CONNECTION_URI` | `machine_password` | yes | yes | `TSW1234STW5678` | 12–128 alphanumeric ASCII characters safe in the connection value; initialized on a new data directory and reused. |
| `TSW_INFISICAL_REDIS_PASSWORD` | Infisical service administrator | Infisical secret manifest and service configuration | `machine_password` | yes | yes | `TSW1234STW5678` | 12–128 alphanumeric ASCII characters; retained as the Redis credential contract although current Compose Redis auth is disabled. |
| `TSW_TRAEFIK_GUI_USERS_HTPASSWD` | Traefik ingress administrator | Traefik dashboard external Docker secret | `htpasswd` | yes | yes | bcrypt cost 12 for `admin` and `TSW1234STW5678` with the fixed catalog salt | ASCII `admin:<bcrypt>` record, exactly 66 bytes; complete hash only, never clear-text material. |

## Reserved and explicitly inactive entries

These entries are present so optional manifest consumers have one defined
resolution if they become part of a future local profile. They are not current
Classic consumers and are not evidence that those stacks are deployed.

| Key | Owner / consumer | Type | Required | Active | Deterministic value | Constraint and rationale |
|---|---|---|---:|---:|---|---|
| `TSW_REDIS_PASSWORD` | Optional standalone Redis authentication | `machine_password` | no | no | `TSW1234STW5678` | Same safe alphanumeric machine-password contract; current Classic Redis service does not consume this key. |
| `TSW_REGISTRY_HTPASSWD` | Optional Docker registry authentication | `htpasswd` | no | no | Same deterministic bcrypt record as the Traefik test admin | Complete bcrypt htpasswd record; Classic uses Nexus registry services instead. |
| `TSW_GRAFANA_ADMIN_PASSWORD` | Optional Grafana admin login | `human_password` | no | no | `TSW1234STW5678` | Same human-password contract; Grafana is not in the current Classic Compose profile. |
| `TSW_PROMETHEUS_BASIC_AUTH_PASSWORD` | Optional Prometheus basic auth | `machine_password` | no | no | `TSW1234STW5678` | Same machine-password contract; Prometheus is not in the current Classic Compose profile. |

## External or runtime-issued values

The following are credentials or credential-bearing resources but deliberately
do not receive deterministic catalog values:

- `TSW_INFISICAL_TOKEN` is an optional operator- or Infisical-issued runtime
  token. It cannot be invented by a test catalog and is not required by the
  current internal-test setup contract.
- Traefik TLS certificate and private-key contents are external or managed
  cryptographic material. `TSW_TRAEFIK_TLS_CERT_SECRET_NAME`,
  `TSW_TRAEFIK_TLS_KEY_SECRET_NAME`, and
  `TSW_TRAEFIK_GUI_USERS_SECRET_NAME` are resource names, not credential
  values; their current defaults remain the Compose/configuration contract.
- Vaultwarden values are opt-in integration-test configuration and are outside
  the supported Classic/internal-test profile.

## Validation API

Catalog construction validates key syntax, required metadata, test-only
marking, encoding, lengths, fixed decoded byte lengths, and format patterns.
The API also provides:

- `validate_internal_test_catalog()` for the active required catalog;
- `validate_internal_test_consumers(keys)` to fail closed when a consumer key
  has no definition; and
- strict `internal_test_credential(key)` lookup, which raises `KeyError` for
  unknown keys instead of inventing a fallback value.

Tests in
`tests/domain/configuration/test_internal_test_credentials.py` cover catalog
completeness, deterministic derivation, JWT signing, bcrypt format, encoded
key lengths, metadata validation, immutable resolution, and missing-entry
failure. No infrastructure is required.
