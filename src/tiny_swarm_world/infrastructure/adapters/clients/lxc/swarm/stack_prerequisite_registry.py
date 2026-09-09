"""Strategy-based prerequisite handling for LXC Swarm stacks."""

from __future__ import annotations

import shlex
import subprocess
import base64
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from tiny_swarm_world.domain.deployment import StackDefinition
from tiny_swarm_world.application.ports.port_tls_contract_resolver import PortTlsContractResolver
from tiny_swarm_world.infrastructure.adapters.clients.lxc.swarm.swarm_stack_runtime import (
    _external_overlay_network_names,
)


ManagerShell = Callable[..., subprocess.CompletedProcess[str]]
SecretExists = Callable[[str], bool]
_TSW_OWNER_LABEL = "tiny-swarm-world.owner"
_TSW_PAIR_LABEL = "tiny-swarm-world.tls-pair"
_TSW_OWNER_VALUE = "tiny-swarm-world"


@dataclass(frozen=True)
class StackPrerequisiteContext:
    stack_name: str
    stack_definition: StackDefinition
    ensure_external_overlay_network: Callable[[str], None]
    ensure_portainer_admin_secret: Callable[[], None]
    ensure_traefik_tls_secrets: Callable[[], None]
    run_manager_shell: ManagerShell


class StackPrerequisiteStrategy(Protocol):
    def supports(self, context: StackPrerequisiteContext) -> bool:
        """Return whether this strategy owns the requested context."""

    def apply(self, context: StackPrerequisiteContext) -> None:
        """Apply the strategy after the registry has selected it."""


class ExternalOverlayNetworkStrategy:
    def supports(self, context: StackPrerequisiteContext) -> bool:
        return True

    def apply(self, context: StackPrerequisiteContext) -> None:
        for network_name in _external_overlay_network_names(context.stack_definition):
            context.ensure_external_overlay_network(network_name)


class TraefikTlsStrategy:
    def supports(self, context: StackPrerequisiteContext) -> bool:
        return context.stack_name == "traefik"

    def apply(self, context: StackPrerequisiteContext) -> None:
        context.ensure_traefik_tls_secrets()


class PortainerAdminSecretStrategy:
    def supports(self, context: StackPrerequisiteContext) -> bool:
        return context.stack_name == "portainer"

    def apply(self, context: StackPrerequisiteContext) -> None:
        context.ensure_portainer_admin_secret()


class SonarqubeKernelStrategy:
    def supports(self, context: StackPrerequisiteContext) -> bool:
        return context.stack_name == "sonarqube"

    def apply(self, context: StackPrerequisiteContext) -> None:
        context.run_manager_shell(
            "sysctl -w vm.max_map_count=524288 fs.file-max=131072 >/dev/null"
        )


class SwaggerAssetPrerequisiteStrategy:
    """Keep an explicit registry hook for Swagger's asset-only preparation."""

    def supports(self, context: StackPrerequisiteContext) -> bool:
        return context.stack_name == "swagger"

    def apply(self, context: StackPrerequisiteContext) -> None:
        # Swagger has no manager-side shell prerequisite; its files are
        # handled by StackAssetTransfer after this registry completes.
        return None


class StackPrerequisiteRegistry:
    """Apply ordered, stack-specific prerequisite strategies."""

    def __init__(self, strategies: Sequence[StackPrerequisiteStrategy] | None = None) -> None:
        self.strategies = tuple(
            strategies
            or (
                ExternalOverlayNetworkStrategy(),
                PortainerAdminSecretStrategy(),
                TraefikTlsStrategy(),
                SonarqubeKernelStrategy(),
                SwaggerAssetPrerequisiteStrategy(),
            )
        )

    def ensure(
        self,
        stack_name: str,
        stack_definition: StackDefinition,
        *,
        ensure_external_overlay_network: Callable[[str], None],
        ensure_portainer_admin_secret: Callable[[], None] | None = None,
        ensure_traefik_tls_secrets: Callable[[], None],
        run_manager_shell: ManagerShell,
    ) -> None:
        context = StackPrerequisiteContext(
            stack_name=stack_name,
            stack_definition=stack_definition,
            ensure_external_overlay_network=ensure_external_overlay_network,
            ensure_portainer_admin_secret=ensure_portainer_admin_secret or (lambda: None),
            ensure_traefik_tls_secrets=ensure_traefik_tls_secrets,
            run_manager_shell=run_manager_shell,
        )
        for strategy in self.strategies:
            if strategy.supports(context):
                strategy.apply(context)

    def ensure_external_overlay_network(
        self,
        name: str,
        *,
        run_manager_shell: ManagerShell,
    ) -> None:
        result = run_manager_shell(
            f"docker network inspect -- {shlex.quote(name)} >/dev/null 2>&1",
            check=False,
        )
        if result.returncode == 0:
            return
        run_manager_shell(
            "docker network create --driver overlay --attachable -- "
            f"{shlex.quote(name)} >/dev/null"
        )

    def ensure_traefik_tls_secrets(
        self,
        cert_secret_name: str,
        key_secret_name: str,
        *,
        external_secret_exists: SecretExists,
        run_manager_shell: ManagerShell,
        tls_contract_resolver: PortTlsContractResolver,
    ) -> None:
        if cert_secret_name == key_secret_name:
            raise ValueError("Traefik TLS certificate and key secret names must be distinct.")
        certificate_exists = external_secret_exists(cert_secret_name)
        private_key_exists = external_secret_exists(key_secret_name)
        contract = tls_contract_resolver.resolve()
        fingerprint = contract.lifecycle_fingerprint
        expected_labels = (_TSW_OWNER_VALUE, fingerprint)
        certificate_labels = (
            _read_secret_labels(cert_secret_name, run_manager_shell)
            if certificate_exists
            else None
        )
        private_key_labels = (
            _read_secret_labels(key_secret_name, run_manager_shell)
            if private_key_exists
            else None
        )
        if certificate_exists and private_key_exists:
            if certificate_labels == expected_labels and private_key_labels == expected_labels:
                return
            raise RuntimeError("Existing Traefik TLS secrets are not a verified owned pair.")
        existing_labels = certificate_labels or private_key_labels
        if existing_labels is not None and existing_labels != expected_labels:
            raise RuntimeError("Partial Traefik TLS secret state is not verified as TSW-owned.")
        certificate = base64.b64encode(contract.certificate_bytes).decode("ascii")
        private_key = base64.b64encode(contract.private_key_bytes).decode("ascii")
        remove_orphan = ""
        if certificate_exists:
            remove_orphan = (
                f"docker secret rm -- {shlex.quote(cert_secret_name)} >/dev/null; "
            )
        elif private_key_exists:
            remove_orphan = (
                f"docker secret rm -- {shlex.quote(key_secret_name)} >/dev/null; "
            )
        script = (
            "set -eu; "
            "tmpdir=$(mktemp -d); "
            "trap 'rm -rf \"$tmpdir\"' EXIT; "
            "umask 077; IFS= read -r cert; IFS= read -r key; "
            "printf '%s' \"$cert\" | base64 -d >\"$tmpdir/tls.crt\"; "
            "printf '%s' \"$key\" | base64 -d >\"$tmpdir/tls.key\"; "
            "chmod 600 \"$tmpdir/tls.crt\" \"$tmpdir/tls.key\"; "
            f"{remove_orphan}"
            f"cert_id=$(docker secret create --label {_TSW_OWNER_LABEL}={_TSW_OWNER_VALUE} "
            f"--label {_TSW_PAIR_LABEL}={shlex.quote(fingerprint)} -- "
            f"{shlex.quote(cert_secret_name)} \"$tmpdir/tls.crt\"); "
            f"if ! key_id=$(docker secret create --label {_TSW_OWNER_LABEL}={_TSW_OWNER_VALUE} "
            f"--label {_TSW_PAIR_LABEL}={shlex.quote(fingerprint)} -- "
            f"{shlex.quote(key_secret_name)} \"$tmpdir/tls.key\"); then "
            "docker secret rm -- \"$cert_id\" >/dev/null 2>&1 || true; "
            "exit 1; fi; printf '%s|%s\n' \"$cert_id\" \"$key_id\""
        )
        create_result = run_manager_shell(script, input_text=f"{certificate}\n{private_key}\n")
        created_ids = _created_secret_ids(create_result.stdout)
        try:
            if not external_secret_exists(cert_secret_name) or not external_secret_exists(key_secret_name):
                raise RuntimeError("Traefik TLS secret-pair reconciliation could not be verified.")
            if (
                _read_secret_labels(cert_secret_name, run_manager_shell) != expected_labels
                or _read_secret_labels(key_secret_name, run_manager_shell) != expected_labels
            ):
                raise RuntimeError("Traefik TLS secret-pair ownership could not be verified.")
        except Exception:
            _rollback_created_secrets(created_ids, run_manager_shell)
            raise


def _read_secret_labels(name: str, run_manager_shell: ManagerShell) -> tuple[str, str]:
    result = run_manager_shell(
        "docker secret inspect --format "
        f"'{{{{ index .Spec.Labels \"{_TSW_OWNER_LABEL}\" }}}}|"
        f"{{{{ index .Spec.Labels \"{_TSW_PAIR_LABEL}\" }}}}' -- {shlex.quote(name)}"
    )
    owner, separator, fingerprint = result.stdout.strip().partition("|")
    if not separator:
        return "", ""
    return owner, fingerprint


def _created_secret_ids(stdout: str | None) -> tuple[str, str]:
    if stdout is None:
        raise RuntimeError("Created Traefik TLS secret identifiers could not be verified.")
    certificate_id, separator, private_key_id = stdout.strip().partition("|")
    if not separator or not all(
        re.fullmatch(r"[a-zA-Z0-9]+", secret_id)
        for secret_id in (certificate_id, private_key_id)
    ):
        raise RuntimeError("Created Traefik TLS secret identifiers could not be verified.")
    return certificate_id, private_key_id


def _rollback_created_secrets(
    created_ids: tuple[str, str],
    run_manager_shell: ManagerShell,
) -> None:
    run_manager_shell(
        "docker secret rm -- " + " ".join(shlex.quote(secret_id) for secret_id in created_ids),
        check=False,
    )
