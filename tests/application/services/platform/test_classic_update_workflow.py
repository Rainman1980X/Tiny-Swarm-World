from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from tiny_swarm_world.application.services.deployment.workflows import (
    DeploymentWorkflowStatus,
)
from tiny_swarm_world.application.services.platform.workflow import (
    ClassicUpdateWorkflow,
    PlatformWorkflowStatus,
)
from tiny_swarm_world.domain.deployment import ComposeServiceDefinition
from tiny_swarm_world.domain.inventory import VerificationStatus
from tiny_swarm_world.domain.preflight import LiveConsent
from tiny_swarm_world.domain.update import ClassicUpdatePlan


def _plan() -> ClassicUpdatePlan:
    return ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")


def _workflow(*, deployment_status: DeploymentWorkflowStatus = DeploymentWorkflowStatus.COMPLETED):
    compose = Mock()
    compose.get_services_of.return_value = (
        ComposeServiceDefinition(name="jenkins", image_ref="old:1"),
    )
    state_store = Mock()
    deployment = SimpleNamespace(
        run=AsyncMock(
            return_value=SimpleNamespace(
                status=deployment_status,
                verification_results=(),
            )
        )
    )
    factory = Mock(return_value=deployment)
    return ClassicUpdateWorkflow(compose, factory, state_store), factory, state_store, deployment


class ClassicUpdateWorkflowTest(unittest.IsolatedAsyncioTestCase):
    async def test_preview_validates_without_consent_state_or_deployment(self) -> None:
        workflow, factory, state_store, _ = _workflow()

        result = await workflow.run(_plan(), preview=True, live_consent=None)

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(VerificationStatus.VERIFIED, result.verification_results[0].status)
        factory.assert_not_called()
        state_store.save.assert_not_called()

    async def test_apply_refuses_missing_consent_before_state_or_deployment(self) -> None:
        workflow, factory, state_store, _ = _workflow()

        result = await workflow.run(_plan(), preview=False, live_consent=None)

        self.assertEqual(PlatformWorkflowStatus.REFUSED, result.status)
        self.assertEqual(VerificationStatus.REFUSED, result.verification_results[0].status)
        factory.assert_not_called()
        state_store.save.assert_not_called()

    async def test_apply_records_rollback_state_and_uses_deployment_port(self) -> None:
        workflow, factory, state_store, deployment = _workflow()
        consent = LiveConsent(live_flag=True, confirmed=True)

        result = await workflow.run(_plan(), preview=False, live_consent=consent)

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertTrue(result.executed)
        state_store.save.assert_called_once_with(_plan())
        factory.assert_called_once_with(_plan())
        deployment.run.assert_awaited_once_with()

    async def test_source_mismatch_blocks_without_downstream_mutation(self) -> None:
        workflow, factory, state_store, _ = _workflow()
        workflow.compose_repository.get_services_of.return_value = (
            ComposeServiceDefinition(name="jenkins", image_ref="other:1"),
        )

        result = await workflow.run(
            _plan(),
            preview=False,
            live_consent=LiveConsent(live_flag=True, confirmed=True),
        )

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual("source_mismatch", result.verification_results[0].evidence["reason"])
        factory.assert_not_called()
        state_store.save.assert_not_called()

    async def test_failed_deployment_is_not_reported_as_completed(self) -> None:
        workflow, _, _, _ = _workflow(
            deployment_status=DeploymentWorkflowStatus.FAILED_TO_APPLY,
        )

        result = await workflow.run(
            _plan(),
            preview=False,
            live_consent=LiveConsent(live_flag=True, confirmed=True),
        )

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, result.status)

    async def test_recover_reverses_the_last_recorded_plan(self) -> None:
        workflow, factory, state_store, _ = _workflow()
        state_store.load.return_value = SimpleNamespace(plan=_plan())
        workflow.compose_repository.get_services_of.return_value = (
            ComposeServiceDefinition(name="jenkins", image_ref="new:1"),
        )

        result = await workflow.recover(
            "jenkins",
            "jenkins",
            preview=False,
            live_consent=LiveConsent(live_flag=True, confirmed=True),
        )

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        factory.assert_called_once_with(_plan().rollback_plan)
        state_store.save.assert_called_once_with(_plan().rollback_plan)

    async def test_recover_without_state_fails_closed(self) -> None:
        workflow, factory, _, _ = _workflow()
        workflow.state_store.load.return_value = None

        result = await workflow.recover(
            "jenkins",
            "jenkins",
            preview=True,
            live_consent=None,
        )

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual("state_not_found", result.verification_results[0].evidence["reason"])
        factory.assert_not_called()
