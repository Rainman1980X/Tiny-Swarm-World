import unittest
from unittest.mock import Mock

from tiny_swarm_world.application.services.credential_resolution import CredentialResolutionService, CredentialResolutionSnapshot
from tests.support.sonar_safe_literals import sensitive_assignment

from tiny_swarm_world.application.ports.clients.port_swarm_stack_runtime import (
    SwarmServiceStatus,
)
from tiny_swarm_world.application.services.deployment.ensure_swarm_stack import (
    EnsureSwarmStack,
)
from tiny_swarm_world.domain.deployment import ServiceStackContract
from tiny_swarm_world.domain.deployment.stack_definition import StackDefinition
from tiny_swarm_world.domain.inventory import VerificationStatus


class TestEnsureSwarmStack(unittest.IsolatedAsyncioTestCase):
    async def test_deploys_loaded_compose_definition_through_runtime_port(self):
        stack_definition = StackDefinition(name="jenkins", compose_content="services: {}")
        repository = _FakeComposeRepository(stack_definition)
        runtime = _FakeSwarmRuntime(stack_exists=True)
        contract = ServiceStackContract("jenkins", ("jenkins",))
        service = EnsureSwarmStack(repository, runtime, contract)

        await service.run()

        self.assertEqual(["jenkins"], repository.requested_stacks)
        self.assertEqual(runtime.deployed_stacks, [(stack_definition, {})])

    async def test_deploys_stack_with_environment_through_runtime_port(self):
        stack_definition = StackDefinition(name="service-access", compose_content="services: {}")
        repository = _FakeComposeRepository(stack_definition)
        runtime = _FakeSwarmRuntime(stack_exists=True)
        service = EnsureSwarmStack(
            repository,
            runtime,
            ServiceStackContract("service-access", ("service-access-dashboard",)),
            stack_environment={"TSW_VAULTWARDEN_ADMIN_TOKEN_SECRET": "operator_defined"},
        )

        await service.run()

        self.assertEqual(
            runtime.deployed_stacks,
            [(stack_definition, {"TSW_VAULTWARDEN_ADMIN_TOKEN_SECRET": "operator_defined"})],
        )

    async def test_deferred_snapshot_changes_only_allowlisted_key_and_records_actual_source(self):
        key = "TSW_JENKINS_ADMIN_PASSWORD"
        snapshot = CredentialResolutionService().resolve_post_bootstrap(
            (key,), secure_values={key: "vault-value"}, operator_values={key: "operator-value"})
        provider = Mock(return_value=snapshot)
        runtime = _FakeSwarmRuntime(stack_exists=True)
        environment = {key: "operator-value", "UNRELATED": "unchanged"}
        service = EnsureSwarmStack(
            _FakeComposeRepository(StackDefinition(name="jenkins", compose_content="services: {}")),
            runtime, ServiceStackContract("jenkins", ("jenkins",)), environment,
            credential_snapshot=provider, credential_keys=(key,),
        )
        provider.assert_not_called()
        await service.run()
        provider.assert_called_once_with()
        self.assertEqual(runtime.deployed_stacks[0][1], {key: "vault-value", "UNRELATED": "unchanged"})
        self.assertEqual(environment[key], "operator-value")
        self.assertEqual(service.stack_environment[key], "operator-value")
        self.assertEqual(service.consumed_credentials.values[key], "vault-value")
        verified = await service.verify()
        self.assertEqual(verified.evidence["resolved_sources"], "vault")
        self.assertNotIn("vault-value", repr(verified.evidence))

    async def test_failed_rerun_clears_consumed_snapshot(self):
        key = "TSW_JENKINS_ADMIN_PASSWORD"
        snapshot = CredentialResolutionService().resolve_post_bootstrap((key,), secure_values={key: "vault-value"})
        for failure in ("provider", "runtime"):
            with self.subTest(failure=failure):
                runtime = _FakeSwarmRuntime(stack_exists=True)
                provider = Mock(return_value=snapshot)
                service = EnsureSwarmStack(
                    _FakeComposeRepository(StackDefinition(name="jenkins", compose_content="services: {}")),
                    runtime, ServiceStackContract("jenkins", ("jenkins",)),
                    credential_snapshot=provider, credential_keys=(key,),
                )
                await service.run()
                self.assertEqual(service.consumed_credentials.values[key], "vault-value")
                if failure == "provider":
                    provider.side_effect = RuntimeError("snapshot unavailable")
                else:
                    runtime.deploy_stack = Mock(side_effect=RuntimeError("deployment failed"))
                with self.assertRaises(RuntimeError):
                    await service.run()
                with self.assertRaisesRegex(ValueError, "No credential snapshot"):
                    _ = service.consumed_credentials
                self.assertFalse(service._applied)

    async def test_missing_or_unrelated_snapshot_blocks_deployment(self):
        key = "TSW_JENKINS_ADMIN_PASSWORD"
        from tiny_swarm_world.domain.configuration.credential_resolution import ResolvedCredential, CredentialSource

        for snapshot in (CredentialResolutionSnapshot({}),
                         CredentialResolutionSnapshot({key: ResolvedCredential(key, " ", CredentialSource.VAULT)}),
                         CredentialResolutionService().resolve_bootstrap(("TSW_PORTAINER_ADMIN_PASSWORD",))):
            with self.subTest(keys=tuple(snapshot.resolutions)):
                runtime = _FakeSwarmRuntime(stack_exists=True)
                service = EnsureSwarmStack(
                    _FakeComposeRepository(StackDefinition(name="jenkins", compose_content="services: {}")),
                    runtime, ServiceStackContract("jenkins", ("jenkins",)),
                    credential_snapshot=lambda: snapshot, credential_keys=(key,),
                )
                with self.assertRaisesRegex(ValueError, "credential snapshot"):
                    await service.run()
                self.assertEqual(runtime.deployed_stacks, [])

    async def test_verify_confirms_stack_registration_and_expected_services(self):
        repository = _FakeComposeRepository(StackDefinition(name="pulsar", compose_content="services: {}"))
        runtime = _FakeSwarmRuntime(
            stack_exists=True,
            services=(SwarmServiceStatus("pulsar_pulsar", 1, 1),),
        )
        service = EnsureSwarmStack(
            repository,
            runtime,
            ServiceStackContract("pulsar", ("pulsar",)),
        )

        verification = await service.verify()

        self.assertEqual(VerificationStatus.VERIFIED, verification.status)
        self.assertEqual(verification.target_id, "deployment:pulsar-stack")
        self.assertEqual("true", verification.evidence["stack_registered"])

    async def test_verify_fails_when_stack_is_missing(self):
        service = EnsureSwarmStack(
            _FakeComposeRepository(StackDefinition(name="pulsar", compose_content="services: {}")),
            _FakeSwarmRuntime(
                stack_exists=False,
                services=(SwarmServiceStatus("pulsar_pulsar", 1, 1),),
            ),
            ServiceStackContract("pulsar", ("pulsar",)),
        )

        verification = await service.verify()

        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, verification.status)
        self.assertEqual(verification.evidence["stack_registered"], "false")

    async def test_verify_fails_when_required_service_is_missing(self):
        service = EnsureSwarmStack(
            _FakeComposeRepository(StackDefinition(name="pulsar", compose_content="services: {}")),
            _FakeSwarmRuntime(stack_exists=True, services=()),
            ServiceStackContract("pulsar", ("pulsar",)),
        )

        verification = await service.verify()

        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, verification.status)
        self.assertEqual(verification.evidence["missing_services"], "pulsar")

    async def test_verify_sanitizes_runtime_failure_and_does_not_deploy(self):
        runtime = _FakeSwarmRuntime(
            stack_exists=True,
            stack_exception=RuntimeError(sensitive_assignment()),
        )
        service = EnsureSwarmStack(
            _FakeComposeRepository(StackDefinition(name="pulsar", compose_content="services: {}")),
            runtime,
            ServiceStackContract("pulsar", ("pulsar",)),
        )

        verification = await service.verify()

        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, verification.status)
        self.assertEqual(runtime.deployed_stacks, [])
        self.assertNotIn("secret", str(verification.to_dict()).casefold())


class _FakeComposeRepository:
    def __init__(self, stack_definition: StackDefinition):
        self.stack_definition = stack_definition
        self.requested_stacks: list[str] = []

    def get_compose_of(self, stack_name: str) -> StackDefinition:
        self.requested_stacks.append(stack_name)
        return self.stack_definition


class _FakeSwarmRuntime:
    def __init__(
        self,
        *,
        stack_exists: bool,
        services: tuple[SwarmServiceStatus, ...] = (),
        stack_exception: Exception | None = None,
    ):
        self._stack_exists = stack_exists
        self._services = services
        self.stack_exception = stack_exception
        self.deployed_stacks: list[tuple[StackDefinition, dict[str, str]]] = []

    def deploy_stack(
        self,
        stack_definition: StackDefinition,
        stack_environment: dict[str, str] | None = None,
    ) -> None:
        self.deployed_stacks.append((stack_definition, dict(stack_environment or {})))

    def stack_exists(self, stack_name: str) -> bool:
        if self.stack_exception is not None:
            raise self.stack_exception
        return self._stack_exists

    def list_stack_services(self, stack_name: str) -> tuple[SwarmServiceStatus, ...]:
        if self.stack_exception is not None:
            raise self.stack_exception
        return self._services

    def external_secret_exists(self, name: str) -> bool:
        return True

    def ensure_external_secret(self, name: str, value: str) -> None:
        return None
