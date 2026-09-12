"""Central credential precedence and lifecycle rules.

The resolver deliberately handles values supplied by adapters as opaque text.
It owns precedence and source classification, but it never contacts Infisical
or any other secret provider. That keeps self-hosted bootstrap free of a
dependency on the service it is starting.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from tiny_swarm_world.domain.configuration.internal_test_credentials import (
    CredentialCatalog,
    internal_test_catalog,
)


class CredentialResolutionPhase(str, Enum):
    """Lifecycle phase in which a credential is resolved."""

    BOOTSTRAP = "bootstrap"
    POST_BOOTSTRAP = "post-bootstrap"


class CredentialSource(str, Enum):
    """Safe source labels permitted in operator-facing evidence."""

    DEFAULT = "default"
    OPERATOR = "operator"
    VAULT = "vault"


class SecureCredentialSource(str, Enum):
    """Provider identity needed to distinguish external from self-hosted use."""

    SELF_HOSTED_INFISICAL = "self-hosted-infisical"
    EXTERNAL_INFISICAL = "external-infisical"


class CredentialResolutionError(ValueError):
    """Raised when a credential source cannot be used in the current phase."""


@dataclass(frozen=True)
class ResolvedCredential:
    """Resolved value plus non-sensitive source metadata."""

    key: str
    value: str
    source: CredentialSource

    def evidence(self) -> dict[str, str]:
        """Return key/source metadata without returning the credential value."""
        return {"key": self.key, "source": self.source.value}


class CredentialResolver:
    """Apply the single credential precedence rule for all lifecycle phases.

    Precedence is secure provider, operator input, then catalog default. A
    self-hosted Infisical value is invalid during bootstrap because that
    instance is not available yet. An external Infisical value may be used at
    bootstrap only when the caller explicitly identifies that source.
    """

    def __init__(self, catalog: CredentialCatalog | None = None) -> None:
        self.catalog = catalog or internal_test_catalog()

    def resolve(
        self,
        key: str,
        *,
        operator_value: str | None = None,
        secure_value: str | None = None,
        secure_source: SecureCredentialSource | None = None,
        phase: CredentialResolutionPhase = CredentialResolutionPhase.BOOTSTRAP,
    ) -> ResolvedCredential:
        phase = CredentialResolutionPhase(phase)
        if secure_source is not None:
            secure_source = SecureCredentialSource(secure_source)
        if secure_value and not secure_value.strip():
            secure_value = None
        if operator_value and not operator_value.strip():
            operator_value = None
        if secure_value:
            if secure_source is None:
                raise CredentialResolutionError(
                    f"Secure credential source must be identified for {key}."
                )
            if (
                phase is CredentialResolutionPhase.BOOTSTRAP
                and secure_source is SecureCredentialSource.SELF_HOSTED_INFISICAL
            ):
                raise CredentialResolutionError(
                    f"Self-hosted Infisical cannot provide {key} before bootstrap; "
                    "use an operator value or an explicitly available external source."
                )
            return ResolvedCredential(key, secure_value, CredentialSource.VAULT)
        if operator_value:
            return ResolvedCredential(key, operator_value, CredentialSource.OPERATOR)
        try:
            value = self.catalog.resolve(key)
        except KeyError as error:
            raise CredentialResolutionError(
                f"No credential default is defined for {key}; provide an operator value."
            ) from error
        return ResolvedCredential(key, value, CredentialSource.DEFAULT)

    def resolve_many(
        self,
        keys: tuple[str, ...],
        *,
        operator_values: Mapping[str, str] | None = None,
        secure_values: Mapping[str, str] | None = None,
        secure_source: SecureCredentialSource | None = None,
        phase: CredentialResolutionPhase = CredentialResolutionPhase.BOOTSTRAP,
    ) -> dict[str, ResolvedCredential]:
        operators = operator_values or {}
        secure = secure_values or {}
        return {
            key: self.resolve(
                key,
                operator_value=operators.get(key),
                secure_value=secure.get(key),
                secure_source=secure_source,
                phase=phase,
            )
            for key in keys
        }
