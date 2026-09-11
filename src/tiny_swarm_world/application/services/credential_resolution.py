"""Application orchestration for credential resolution and source evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from tiny_swarm_world.domain.configuration.credential_resolution import (
    CredentialResolutionError,
    CredentialResolutionPhase,
    CredentialResolver,
    CredentialSource,
    ResolvedCredential,
    SecureCredentialSource,
)


CREDENTIAL_SOURCE_MAP_ENVIRONMENT = "TSW_CREDENTIAL_SOURCE_MAP"


@dataclass(frozen=True)
class CredentialResolutionSnapshot:
    """Immutable in-memory values with separately safe source metadata."""

    resolutions: Mapping[str, ResolvedCredential]

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolutions", dict(self.resolutions))

    @property
    def values(self) -> dict[str, str]:
        return {key: item.value for key, item in self.resolutions.items()}

    @property
    def sources(self) -> dict[str, CredentialSource]:
        return {key: item.source for key, item in self.resolutions.items()}

    def source_metadata(self) -> str:
        return json.dumps(
            {key: source.value for key, source in sorted(self.sources.items())},
            separators=(",", ":"),
            sort_keys=True,
        )

    def compare_to(
        self,
        before: "CredentialResolutionSnapshot",
    ) -> "CredentialResolutionComparison":
        """Compare effective state without exposing credential material.

        Values are compared only in memory. The returned evidence contains
        credential names, source labels, and equality/change booleans; it does
        not contain values, hashes, or fingerprints.
        """
        keys = tuple(sorted(set(before.resolutions) | set(self.resolutions)))
        changed_keys = tuple(
            key
            for key in keys
            if before.resolutions.get(key, None) is None
            or self.resolutions.get(key, None) is None
            or before.resolutions[key].value != self.resolutions[key].value
        )
        changed_source_keys = tuple(
            key
            for key in keys
            if before.resolutions.get(key, None) is None
            or self.resolutions.get(key, None) is None
            or before.resolutions[key].source != self.resolutions[key].source
        )
        return CredentialResolutionComparison(
            keys=keys,
            changed_keys=changed_keys,
            changed_source_keys=changed_source_keys,
        )


@dataclass(frozen=True)
class CredentialResolutionComparison:
    """Safe before/after evidence for reconcile, restart, or transitions."""

    keys: tuple[str, ...]
    changed_keys: tuple[str, ...]
    changed_source_keys: tuple[str, ...]

    @property
    def values_equal(self) -> bool:
        return not self.changed_keys

    @property
    def sources_equal(self) -> bool:
        return not self.changed_source_keys

    @property
    def stable(self) -> bool:
        return self.values_equal and self.sources_equal

    def evidence(self) -> dict[str, object]:
        """Return comparison facts suitable for protected evidence."""
        return {
            "keys": list(self.keys),
            "values_equal": self.values_equal,
            "sources_equal": self.sources_equal,
            "changed_keys": list(self.changed_keys),
            "changed_source_keys": list(self.changed_source_keys),
        }


class CredentialResolutionService:
    """Apply the domain policy at bootstrap and post-bootstrap boundaries."""

    def __init__(self, resolver: CredentialResolver | None = None) -> None:
        self.resolver = resolver or CredentialResolver()

    def resolve_bootstrap(
        self,
        keys: tuple[str, ...],
        *,
        operator_values: Mapping[str, str] | None = None,
    ) -> CredentialResolutionSnapshot:
        return CredentialResolutionSnapshot(
            self.resolver.resolve_many(
                keys,
                operator_values=operator_values,
                phase=CredentialResolutionPhase.BOOTSTRAP,
            )
        )

    def resolve_post_bootstrap(
        self,
        keys: tuple[str, ...],
        *,
        operator_values: Mapping[str, str] | None = None,
        secure_values: Mapping[str, str] | None = None,
        secure_source: SecureCredentialSource = SecureCredentialSource.SELF_HOSTED_INFISICAL,
    ) -> CredentialResolutionSnapshot:
        return CredentialResolutionSnapshot(
            self.resolver.resolve_many(
                keys,
                operator_values=operator_values,
                secure_values=secure_values,
                secure_source=secure_source,
                phase=CredentialResolutionPhase.POST_BOOTSTRAP,
            )
        )


def decode_source_metadata(raw: str | None) -> dict[str, CredentialSource]:
    """Parse process transport metadata without ever accepting raw values."""
    if not raw or not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CredentialResolutionError(
            f"{CREDENTIAL_SOURCE_MAP_ENVIRONMENT} is not valid source metadata."
        ) from error
    if not isinstance(payload, dict):
        raise CredentialResolutionError(
            f"{CREDENTIAL_SOURCE_MAP_ENVIRONMENT} must be a JSON object."
        )
    decoded: dict[str, CredentialSource] = {}
    for key, source in payload.items():
        if not isinstance(key, str) or not key.startswith("TSW_"):
            raise CredentialResolutionError(
                f"{CREDENTIAL_SOURCE_MAP_ENVIRONMENT} contains an invalid credential key."
            )
        try:
            decoded[key] = CredentialSource(source)
        except ValueError as error:
            raise CredentialResolutionError(
                f"{CREDENTIAL_SOURCE_MAP_ENVIRONMENT} contains an unsupported source for {key}."
            ) from error
    return decoded
