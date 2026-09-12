from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping

from tiny_swarm_world.application.services.credential_resolution import CredentialResolutionSnapshot

from tiny_swarm_world.application.ports.clients.port_swarm_stack_runtime import (
    PortSwarmStackRuntime,
    SwarmServiceStatus,
)
from tiny_swarm_world.application.ports.repositories.port_compose_file_repository import (
    PortComposeFileRepository,
)
from tiny_swarm_world.domain.deployment import ServiceStackContract
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus


class EnsureSwarmStack:
    def __init__(
        self,
        compose_repository: PortComposeFileRepository,
        swarm_runtime: PortSwarmStackRuntime,
        service_stack: ServiceStackContract,
        stack_environment: Mapping[str, str] | None = None,
        *,
        credential_snapshot: Callable[[], CredentialResolutionSnapshot] | None = None,
        credential_keys: tuple[str, ...] = (),
    ):
        self.compose_repository = compose_repository
        self.swarm_runtime = swarm_runtime
        self.service_stack = service_stack
        self.stack_environment = dict(stack_environment or {})
        self.deployment_target_id = service_stack.stack_target_id
        self.verification_target_id = service_stack.stack_target_id
        if bool(credential_snapshot) != bool(credential_keys):
            raise ValueError("A credential snapshot provider requires an explicit key allowlist.")
        self.credential_snapshot = credential_snapshot
        self.credential_keys = tuple(credential_keys)
        self._consumed_credentials: CredentialResolutionSnapshot | None = None
        self._applied = False

    @property
    def consumed_credentials(self) -> CredentialResolutionSnapshot:
        if self._consumed_credentials is None:
            raise ValueError("No credential snapshot has been consumed by a successful deployment.")
        return CredentialResolutionSnapshot(self._consumed_credentials.resolutions)

    async def run(self) -> None:
        await asyncio.sleep(0)
        self._applied = False
        self._consumed_credentials = None
        environment = dict(self.stack_environment)
        consumed = None
        if self.credential_snapshot is not None:
            snapshot = self.credential_snapshot()
            if set(snapshot.resolutions) != set(self.credential_keys) or any(
                not snapshot.resolutions[key].value.strip() for key in self.credential_keys
            ):
                raise ValueError("Resolved credential snapshot does not match required keys.")
            consumed = CredentialResolutionSnapshot(snapshot.resolutions)
            environment.update(consumed.values)
        stack_definition = self.compose_repository.get_compose_of(self.service_stack.stack_name)
        self.swarm_runtime.deploy_stack(stack_definition, environment)
        self._consumed_credentials = consumed
        self._applied = True

    async def verify(self) -> VerificationResult:
        await asyncio.sleep(0)
        if self._applied:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.VERIFIED,
                message="Swarm stack deploy command completed.",
                evidence={
                    **_stack_evidence(
                        self.service_stack,
                        stack_registered="deploy_command_completed",
                        observed_services=self.service_stack.required_services,
                    ),
                    **({"resolved_sources": ",".join(
                        self._consumed_credentials.sources[key].value for key in self.credential_keys)}
                       if self._consumed_credentials is not None else {}),
                },
            )
        try:
            stack_exists = self.swarm_runtime.stack_exists(self.service_stack.stack_name)
            observed_services = _observed_service_names(
                self.service_stack.stack_name,
                self.swarm_runtime.list_stack_services(self.service_stack.stack_name),
            )
        except Exception as exc:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.FAILED_TO_VERIFY,
                message=f"Swarm stack registration verification failed: {exc.__class__.__name__}",
                evidence=_stack_evidence(self.service_stack, stack_registered="unknown"),
            )

        missing_services = tuple(
            service
            for service in self.service_stack.required_services
            if service not in observed_services
        )
        if stack_exists and not missing_services:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.VERIFIED,
                message="Swarm stack is registered with expected services.",
                evidence=_stack_evidence(
                    self.service_stack,
                    stack_registered="true",
                    observed_services=observed_services,
                ),
            )

        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.FAILED_TO_VERIFY,
            message="Swarm stack is missing expected service registrations.",
            evidence=_stack_evidence(
                self.service_stack,
                stack_registered=str(stack_exists).lower(),
                missing_services=missing_services,
                observed_services=observed_services,
            ),
        )


def _observed_service_names(
    stack_name: str,
    services: tuple[SwarmServiceStatus, ...],
) -> tuple[str, ...]:
    prefix = f"{stack_name}_"
    observed: list[str] = []
    for service in services:
        service_name = getattr(service, "service_name", "")
        if service_name.startswith(prefix):
            observed.append(service_name[len(prefix) :])
        elif service_name:
            observed.append(service_name)
    return tuple(sorted(observed))


def _stack_evidence(
    service_stack: ServiceStackContract,
    *,
    stack_registered: str,
    missing_services: tuple[str, ...] = (),
    observed_services: tuple[str, ...] = (),
) -> dict[str, str]:
    return {
        "missing_services": ",".join(missing_services),
        "observed_services": ",".join(observed_services),
        "phase": "verify",
        "required_services": ",".join(service_stack.required_services),
        "stack_name": service_stack.stack_name,
        "stack_registered": stack_registered,
    }
