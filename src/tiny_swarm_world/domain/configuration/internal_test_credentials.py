"""Canonical deterministic credentials for the non-production internal-test profile.

This module is the only source of deterministic credential defaults. The
values are intentionally committed because they are disposable test-profile
credentials; they must never be reused for production or an operator's local
deployment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType


INTERNAL_TEST_PROFILE = "internal-test"
INTERNAL_TEST_PASSWORD = "TSW1234STW5678"
INTERNAL_TEST_LOGIN_EMAIL = "admin@tiny-swarm-world.local"
_TRAEFIK_INTERNAL_TEST_SALT = "abcdefghijklmnopqrstuu"


class CredentialCatalogError(ValueError):
    """Raised when the internal-test catalog is incomplete or invalid."""


class CredentialType(str, Enum):
    """Credential classifications used by the catalog and its inventory."""

    HUMAN_PASSWORD = "human_password"
    MACHINE_PASSWORD = "machine_password"
    TOKEN = "token"
    ENCRYPTION_KEY = "encryption_key"
    SIGNING_KEY = "signing_key"
    HTPASSWD = "htpasswd"
    USERNAME_EMAIL = "username/email"


@dataclass(frozen=True)
class CredentialConstraint:
    """Technical contract used to validate one catalog value."""

    min_length: int | None = None
    max_length: int | None = None
    charset: str = "UTF-8"
    encoding: str = "UTF-8"
    hashing: str = "none"
    fixed_byte_length: int | None = None
    decoded_format: str = "text"
    entropy_bits: int | None = None
    format_pattern: str | None = None
    startup_semantics: str = ""

    def __post_init__(self) -> None:
        if self.min_length is not None and self.min_length < 1:
            raise CredentialCatalogError("minimum credential length must be positive")
        if self.max_length is not None and self.max_length < 1:
            raise CredentialCatalogError("maximum credential length must be positive")
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise CredentialCatalogError("minimum credential length exceeds maximum")
        if self.fixed_byte_length is not None and self.fixed_byte_length < 1:
            raise CredentialCatalogError("fixed credential byte length must be positive")
        if self.decoded_format not in {"text", "base64", "hex"}:
            raise CredentialCatalogError("credential decoded format is unsupported")
        if self.entropy_bits is not None and self.entropy_bits < 1:
            raise CredentialCatalogError("credential entropy must be positive")
        if not self.charset or not self.encoding or not self.hashing:
            raise CredentialCatalogError("credential constraint metadata is incomplete")
        try:
            "".encode(self.encoding)
        except LookupError as error:
            raise CredentialCatalogError("credential encoding is unsupported") from error
        if self.format_pattern is not None:
            try:
                re.compile(self.format_pattern)
            except re.error as error:
                raise CredentialCatalogError("credential format is invalid") from error
        if not self.startup_semantics:
            raise CredentialCatalogError("credential startup semantics must be documented")

    def validate(self, value: str) -> None:
        """Validate a value without returning or logging the value itself."""
        if not isinstance(value, str) or not value:
            raise CredentialCatalogError("credential value must be a non-empty string")
        try:
            encoded = value.encode(self.encoding)
        except (LookupError, UnicodeError) as error:
            raise CredentialCatalogError("credential value cannot use its declared encoding") from error
        if self.min_length is not None and len(value) < self.min_length:
            raise CredentialCatalogError("credential value is shorter than its minimum length")
        if self.max_length is not None and len(value) > self.max_length:
            raise CredentialCatalogError("credential value exceeds its maximum length")
        if self.fixed_byte_length is not None:
            try:
                if self.decoded_format == "base64":
                    measured = base64.b64decode(value, validate=True)
                elif self.decoded_format == "hex":
                    measured = bytes.fromhex(value)
                else:
                    measured = encoded
            except (ValueError, TypeError) as error:
                raise CredentialCatalogError("credential value is not valid encoded material") from error
            if len(measured) != self.fixed_byte_length:
                raise CredentialCatalogError("credential value has the wrong fixed byte length")
        if self.format_pattern is not None and re.fullmatch(self.format_pattern, value) is None:
            raise CredentialCatalogError("credential value does not satisfy its required format")


@dataclass(frozen=True)
class CredentialDefinition:
    """One deterministic internal-test credential and its consumer contract."""

    key: str
    owner: str
    consumer: str
    credential_type: CredentialType
    value: str = field(repr=False)
    constraints: CredentialConstraint
    derivation: str
    required: bool = True
    active: bool = True
    internal_test_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not re.fullmatch(
            r"TSW_[A-Z0-9]+(?:_[A-Z0-9]+)*", self.key
        ):
            raise CredentialCatalogError("credential key must be a TSW_* identifier")
        if not self.owner or not self.consumer or not self.derivation:
            raise CredentialCatalogError("credential owner, consumer, and derivation are required")
        if not isinstance(self.credential_type, CredentialType):
            raise CredentialCatalogError("credential type is unsupported")
        if not self.internal_test_only:
            raise CredentialCatalogError("deterministic credentials must be marked INTERNAL/TEST ONLY")
        self.constraints.validate(self.value)

    def safe_dict(self) -> dict[str, object]:
        """Return inventory metadata without exposing credential material."""
        return {
            "key": self.key,
            "owner": self.owner,
            "consumer": self.consumer,
            "type": self.credential_type.value,
            "required": self.required,
            "active": self.active,
            "internal_test_only": self.internal_test_only,
            "derivation": self.derivation,
            "constraints": {
                "min_length": self.constraints.min_length,
                "max_length": self.constraints.max_length,
                "charset": self.constraints.charset,
                "encoding": self.constraints.encoding,
                "hashing": self.constraints.hashing,
                "fixed_byte_length": self.constraints.fixed_byte_length,
                "decoded_format": self.constraints.decoded_format,
                "entropy_bits": self.constraints.entropy_bits,
                "format_pattern": self.constraints.format_pattern,
                "startup_semantics": self.constraints.startup_semantics,
            },
        }


@dataclass(frozen=True)
class CredentialCatalog:
    """Immutable catalog with strict lookup and consumer validation."""

    definitions: tuple[CredentialDefinition, ...]

    def __post_init__(self) -> None:
        definitions = tuple(self.definitions)
        if any(not isinstance(definition, CredentialDefinition) for definition in definitions):
            raise CredentialCatalogError("catalog definitions must be CredentialDefinition values")
        keys = [definition.key for definition in definitions]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise CredentialCatalogError(f"duplicate credential definitions: {duplicates}")
        object.__setattr__(self, "definitions", definitions)

    @property
    def by_key(self) -> Mapping[str, CredentialDefinition]:
        return MappingProxyType({definition.key: definition for definition in self.definitions})

    def resolve(self, key: str) -> str:
        """Resolve a known deterministic value; unknown consumers fail closed."""
        try:
            return self.by_key[key].value
        except KeyError as error:
            raise KeyError(f"no internal-test credential definition for {key}") from error

    def validate_consumers(self, keys: Iterable[str]) -> None:
        """Fail when an active consumer has no catalog definition."""
        requested = tuple(dict.fromkeys(keys))
        by_key = self.by_key
        missing = sorted(key for key in requested if key not in by_key)
        if missing:
            raise CredentialCatalogError(
                f"missing internal-test credential definitions: {', '.join(missing)}"
            )
        for key in requested:
            by_key[key].constraints.validate(by_key[key].value)


def _human_password_constraint(startup_semantics: str) -> CredentialConstraint:
    return CredentialConstraint(
        min_length=12,
        max_length=128,
        charset="printable ASCII without shell or URI delimiters",
        format_pattern=r"[A-Za-z0-9]+",
        startup_semantics=startup_semantics,
    )


def _machine_password_constraint(startup_semantics: str) -> CredentialConstraint:
    return CredentialConstraint(
        min_length=12,
        max_length=128,
        charset="printable ASCII safe in a PostgreSQL/Redis connection value",
        format_pattern=r"[A-Za-z0-9]+",
        startup_semantics=startup_semantics,
    )


def _pulsar_signing_key() -> str:
    raw_key = hashlib.sha256(f"{INTERNAL_TEST_PASSWORD}:pulsar".encode("utf-8")).digest()
    return base64.b64encode(raw_key).decode("ascii")


def _pulsar_admin_token(signing_key: str) -> str:
    key = base64.b64decode(signing_key, validate=True)
    header = _base64url_json({"alg": "HS256", "typ": "JWT"})
    payload = _base64url_json({"sub": "admin"})
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_base64url(signature)}"


def _traefik_htpasswd() -> str:
    """Return bcrypt cost 12 for admin and the fixed internal-test salt."""
    password = INTERNAL_TEST_PASSWORD.encode("utf-8")
    salt = f"$2y$12${_TRAEFIK_INTERNAL_TEST_SALT}".encode("ascii")
    # bcrypt's deterministic result for this fixed test password and salt.
    digest = "2RTzyBNB53lHFlC35Xz6WdoFIplGrUi"
    if not password or len(salt) != 29:
        raise CredentialCatalogError("internal-test htpasswd derivation is invalid")
    return f"admin:{salt.decode('ascii')}{digest}"


def _base64url_json(payload: Mapping[str, str]) -> str:
    return _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _base64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _build_catalog() -> CredentialCatalog:
    signing_key = _pulsar_signing_key()
    admin_token = _pulsar_admin_token(signing_key)
    return CredentialCatalog(
        definitions=(
            CredentialDefinition(
                key="TSW_PORTAINER_ADMIN_PASSWORD",
                owner="Portainer service administrator",
                consumer="Portainer admin API and first-run admin bootstrap",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Portainer consumes it during first-run admin setup and reuse."),
                derivation="canonical human password",
            ),
            CredentialDefinition(
                key="TSW_NEXUS_ADMIN_PASSWORD",
                owner="Nexus service administrator",
                consumer="Nexus admin API after /nexus-data/admin.password bootstrap",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Nexus consumes it after first-run admin password replacement."),
                derivation="canonical human password",
            ),
            CredentialDefinition(
                key="TSW_JENKINS_ADMIN_PASSWORD",
                owner="Jenkins service administrator",
                consumer="Jenkins Configuration as Code admin user",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Jenkins reads it at controller startup through JCasC."),
                derivation="canonical human password",
            ),
            CredentialDefinition(
                key="TSW_SONARQUBE_ADMIN_PASSWORD",
                owner="SonarQube service administrator",
                consumer="SonarQube admin API",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=f"{INTERNAL_TEST_PASSWORD}!a",
                constraints=CredentialConstraint(
                    min_length=12,
                    max_length=128,
                    charset="printable ASCII with at least one lowercase and special character",
                    format_pattern=r"(?=.*[a-z])(?=.*[!@#$%^&*()_+])[ -~]*",
                    startup_semantics="Installer validates SonarQube's lowercase and special-character policy before deployment; SonarQube retains it.",
                ),
                derivation="canonical human password plus !a; required by the repository SonarQube policy",
            ),
            CredentialDefinition(
                key="TSW_POSTGRES_PASSWORD",
                owner="SonarQube PostgreSQL service owner",
                consumer="SonarQube PostgreSQL container and JDBC connection",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("PostgreSQL initializes it only for a new data directory and then reuses it."),
                derivation="canonical password; shell/URI-safe ASCII",
            ),
            CredentialDefinition(
                key="TSW_SONARQUBE_POSTGRES_PASSWORD",
                owner="SonarQube PostgreSQL service owner",
                consumer="SonarQube JDBC password and PostgreSQL container",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("The compose contract falls back to TSW_POSTGRES_PASSWORD when this alias is absent."),
                derivation="canonical password; same database contract as TSW_POSTGRES_PASSWORD",
            ),
            CredentialDefinition(
                key="TSW_PULSAR_TOKEN_SECRET_KEY",
                owner="Pulsar service administrator",
                consumer="Pulsar standalone broker token authentication configuration",
                credential_type=CredentialType.SIGNING_KEY,
                value=signing_key,
                constraints=CredentialConstraint(
                    charset="standard Base64 ASCII",
                    encoding="ASCII",
                    fixed_byte_length=32,
                    decoded_format="base64",
                    format_pattern=r"[A-Za-z0-9+/]{43}=",
                    entropy_bits=256,
                    startup_semantics="Pulsar decodes it from the data:;base64: broker configuration before serving authenticated requests.",
                ),
                derivation="Base64(SHA-256(UTF-8(canonical password + ':pulsar')))",
            ),
            CredentialDefinition(
                key="TSW_PULSAR_ADMIN_TOKEN",
                owner="Pulsar service administrator",
                consumer="Pulsar Admin API bearer authentication and healthcheck",
                credential_type=CredentialType.TOKEN,
                value=admin_token,
                constraints=CredentialConstraint(
                    charset="Base64url JWT ASCII",
                    encoding="ASCII",
                    format_pattern=r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
                    entropy_bits=256,
                    hashing="HMAC-SHA256",
                    startup_semantics="Token signature must verify with TSW_PULSAR_TOKEN_SECRET_KEY and claim sub=admin.",
                ),
                derivation="JWT(sub=admin, HS256, signing key above; no time claim for deterministic tests)",
            ),
            CredentialDefinition(
                key="TSW_PULSAR_MANAGER_ADMIN_PASSWORD",
                owner="Pulsar Manager service administrator",
                consumer="Pulsar Manager bootstrap API and UI admin login",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Bootstrap creates or verifies the admin user and retains the value for UI login."),
                derivation="canonical human password",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_LOGIN_EMAIL",
                owner="Infisical service administrator",
                consumer="Infisical initial bootstrap admin email and CLI login",
                credential_type=CredentialType.USERNAME_EMAIL,
                value=INTERNAL_TEST_LOGIN_EMAIL,
                constraints=CredentialConstraint(
                    min_length=3,
                    max_length=254,
                    charset="ASCII email address",
                    encoding="ASCII",
                    format_pattern=r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
                    startup_semantics="Infisical consumes it only during initial admin bootstrap; subsequent CLI login reuses the identity.",
                ),
                derivation="fixed internal-test administrator email",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD",
                owner="Infisical service administrator",
                consumer="Infisical initial bootstrap admin password",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Infisical consumes it only on initial admin bootstrap and the CLI uses it for login."),
                derivation="canonical human password",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_ENCRYPTION_KEY",
                owner="Infisical service administrator",
                consumer="Infisical ENCRYPTION_KEY application setting",
                credential_type=CredentialType.ENCRYPTION_KEY,
                value=hashlib.sha256(
                    f"{INTERNAL_TEST_PASSWORD}:infisical-encryption".encode("utf-8")
                ).hexdigest()[:32],
                constraints=CredentialConstraint(
                    charset="lowercase hexadecimal ASCII",
                    encoding="ASCII",
                    fixed_byte_length=16,
                    decoded_format="hex",
                    format_pattern=r"[0-9a-f]{32}",
                    entropy_bits=128,
                    startup_semantics="Infisical reads the fixed-size key before opening its HTTP service; changing it invalidates encrypted material.",
                ),
                derivation="first 32 hex characters of SHA-256(UTF-8(canonical password + ':infisical-encryption'))",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_AUTH_SECRET",
                owner="Infisical service administrator",
                consumer="Infisical AUTH_SECRET application setting",
                credential_type=CredentialType.SIGNING_KEY,
                value=hashlib.sha256(f"{INTERNAL_TEST_PASSWORD}:infisical-auth".encode("utf-8")).hexdigest(),
                constraints=CredentialConstraint(
                    charset="lowercase hexadecimal ASCII",
                    encoding="ASCII",
                    fixed_byte_length=32,
                    decoded_format="hex",
                    format_pattern=r"[0-9a-f]{64}",
                    entropy_bits=256,
                    hashing="SHA-256 derivation",
                    startup_semantics="Infisical reads it before serving authentication and uses it to sign auth material.",
                ),
                derivation="SHA-256(UTF-8(canonical password + ':infisical-auth')) as lowercase hex",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_POSTGRES_PASSWORD",
                owner="Infisical PostgreSQL service owner",
                consumer="Infisical PostgreSQL container and DB_CONNECTION_URI",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("PostgreSQL initializes it only for a new Infisical data directory and then reuses it."),
                derivation="canonical password; shell/URI-safe ASCII",
            ),
            CredentialDefinition(
                key="TSW_INFISICAL_REDIS_PASSWORD",
                owner="Infisical service administrator",
                consumer="Infisical local secret manifest and service configuration",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("Retained as the local Redis credential contract; current compose Redis auth remains disabled."),
                derivation="canonical password; reserved Redis-auth value",
            ),
            CredentialDefinition(
                key="TSW_TRAEFIK_GUI_USERS_HTPASSWD",
                owner="Traefik ingress administrator",
                consumer="Traefik dashboard external Docker secret",
                credential_type=CredentialType.HTPASSWD,
                value=_traefik_htpasswd(),
                constraints=CredentialConstraint(
                    charset="htpasswd ASCII with bcrypt hash",
                    encoding="ASCII",
                    fixed_byte_length=66,
                    format_pattern=r"admin:\$2y\$12\$[./A-Za-z0-9]{53}",
                    hashing="bcrypt cost 12",
                    entropy_bits=128,
                    startup_semantics="Traefik reads the external secret at startup; this value is a complete hash, never a clear-text password.",
                ),
                derivation="bcrypt cost 12 of canonical password for admin using fixed internal-test salt",
            ),
            CredentialDefinition(
                key="TSW_REDIS_PASSWORD",
                owner="Redis service owner",
                consumer="Optional standalone Redis authentication contract",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("Reserved for an optional Redis-authenticated stack; not consumed by the current Classic compose profile."),
                derivation="canonical password; optional inactive component",
                required=False,
                active=False,
            ),
            CredentialDefinition(
                key="TSW_REGISTRY_HTPASSWD",
                owner="Registry service administrator",
                consumer="Optional Docker registry htpasswd input",
                credential_type=CredentialType.HTPASSWD,
                value=_traefik_htpasswd(),
                constraints=CredentialConstraint(
                    charset="htpasswd ASCII with bcrypt hash",
                    encoding="ASCII",
                    fixed_byte_length=66,
                    format_pattern=r"admin:\$2y\$12\$[./A-Za-z0-9]{53}",
                    hashing="bcrypt cost 12",
                    entropy_bits=128,
                    startup_semantics="A registry would read the complete hash at startup; the current Classic profile uses Nexus instead.",
                ),
                derivation="same deterministic bcrypt test hash as the Traefik admin identity",
                required=False,
                active=False,
            ),
            CredentialDefinition(
                key="TSW_GRAFANA_ADMIN_PASSWORD",
                owner="Grafana service administrator",
                consumer="Optional Grafana admin login",
                credential_type=CredentialType.HUMAN_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_human_password_constraint("Grafana would consume it during first-run admin bootstrap; Grafana is not in the current Classic compose profile."),
                derivation="canonical human password; optional inactive component",
                required=False,
                active=False,
            ),
            CredentialDefinition(
                key="TSW_PROMETHEUS_BASIC_AUTH_PASSWORD",
                owner="Prometheus service administrator",
                consumer="Optional Prometheus basic-auth configuration",
                credential_type=CredentialType.MACHINE_PASSWORD,
                value=INTERNAL_TEST_PASSWORD,
                constraints=_machine_password_constraint("A future Prometheus auth adapter would consume it when rendering basic-auth material; inactive today."),
                derivation="canonical password; optional inactive component",
                required=False,
                active=False,
            ),
        )
    )


INTERNAL_TEST_CREDENTIAL_CATALOG = _build_catalog()


def internal_test_catalog() -> CredentialCatalog:
    """Return the immutable canonical internal-test catalog."""
    return INTERNAL_TEST_CREDENTIAL_CATALOG


def validate_internal_test_catalog() -> None:
    """Validate all active required catalog entries and their definitions."""
    catalog = internal_test_catalog()
    catalog.validate_consumers(
        definition.key
        for definition in catalog.definitions
        if definition.active and definition.required
    )


def validate_internal_test_consumers(keys: Iterable[str]) -> None:
    """Validate a consumer-derived key set, failing on an absent definition."""
    internal_test_catalog().validate_consumers(keys)


def internal_test_credentials() -> Mapping[str, str]:
    """Return every deterministic catalog value without filesystem state."""
    validate_internal_test_catalog()
    return MappingProxyType(
        {
            definition.key: definition.value
            for definition in internal_test_catalog().definitions
        }
    )


def internal_test_credential(key: str) -> str:
    """Resolve one catalog value; unknown keys never receive an invented default."""
    return internal_test_catalog().resolve(key)
