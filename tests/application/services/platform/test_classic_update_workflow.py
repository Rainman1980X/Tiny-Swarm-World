from __future__ import annotations

from types import SimpleNamespace
import asyncio
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, Mock

from tiny_swarm_world.application.services.deployment.workflows import (
    DeploymentWorkflowStatus,
)
from tiny_swarm_world.application.services.platform.workflow import (
    ClassicUpdateWorkflow,
    PlatformWorkflowStatus,
)
from tiny_swarm_world.domain.deployment import ComposeServiceDefinition
from tiny_swarm_world.domain.inventory import (
    VerificationStatus,
    VerificationEvidenceScope,
)
from tiny_swarm_world.domain.preflight import LiveConsent
from tiny_swarm_world.domain.update import (
    ClassicUpdatePlan,
    UpdateRuntimeObservation,
    UpdateTaskObservation,
)
from tiny_swarm_world.application.ports.update import (
    PortUpdateRuntimeObserver,
    UpdateObservationError,
)


def _plan() -> ClassicUpdatePlan:
    return ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")


def _runtime(image="old:1", *, task_image=None, state="running", rollout="completed"):
    return UpdateRuntimeObservation(
        "jenkins",
        "jenkins",
        "service-id",
        1,
        image,
        1,
        (UpdateTaskObservation("task-id", task_image or image, state, "running"),),
        rollout,
    )


def _workflow(
    *,
    deployment_status: DeploymentWorkflowStatus = DeploymentWorkflowStatus.COMPLETED,
    initial="old:1",
    target="new:1",
):
    compose = Mock()
    compose.get_services_of.return_value = (
        ComposeServiceDefinition(name="jenkins", image_ref="old:1"),
    )
    state_store = Mock()
    state_store.load.return_value = None
    observer = Mock(spec=PortUpdateRuntimeObserver)
    observer.observe = AsyncMock(side_effect=[_runtime(initial), _runtime(target)])
    deployment = SimpleNamespace(
        run=AsyncMock(
            return_value=SimpleNamespace(
                status=deployment_status,
                verification_results=(),
            )
        )
    )
    factory = Mock(return_value=deployment)
    return (
        ClassicUpdateWorkflow(
            compose,
            factory,
            state_store,
            observer,
            verification_attempts=2,
            poll_interval_seconds=0,
        ),
        factory,
        state_store,
        deployment,
    )


class ClassicUpdateWorkflowTest(unittest.IsolatedAsyncioTestCase):
    async def test_static_preview_defers_source_qualification_even_with_stale_compose(
        self,
    ) -> None:
        workflow, factory, store, _ = _workflow()
        workflow.compose_repository.get_services_of.return_value = (
            ComposeServiceDefinition(name="jenkins", image_ref="stale:1"),
        )
        result = await workflow.run(_plan(), preview=True, live_consent=None)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(
            "false", result.verification_results[0].evidence["runtime_observed"]
        )
        self.assertEqual(
            VerificationEvidenceScope.STATIC,
            result.verification_results[0].evidence_scope,
        )
        workflow.runtime_observer.observe.assert_not_awaited()
        store.save.assert_not_called()
        factory.assert_not_called()

    async def test_preview_validates_without_consent_state_or_deployment(self) -> None:
        workflow, factory, state_store, _ = _workflow()

        result = await workflow.run(_plan(), preview=True, live_consent=None)

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(
            VerificationStatus.VERIFIED, result.verification_results[0].status
        )
        factory.assert_not_called()
        state_store.save.assert_not_called()
        workflow.runtime_observer.observe.assert_not_awaited()

    async def test_apply_refuses_missing_consent_before_state_or_deployment(
        self,
    ) -> None:
        workflow, factory, state_store, _ = _workflow()

        result = await workflow.run(_plan(), preview=False, live_consent=None)

        self.assertEqual(PlatformWorkflowStatus.REFUSED, result.status)
        self.assertEqual(
            VerificationStatus.REFUSED, result.verification_results[0].status
        )
        factory.assert_not_called()
        state_store.save.assert_not_called()
        workflow.runtime_observer.observe.assert_not_awaited()

    async def test_apply_records_rollback_state_and_uses_deployment_port(self) -> None:
        workflow, factory, state_store, deployment = _workflow()
        consent = LiveConsent(live_flag=True, confirmed=True)

        result = await workflow.run(_plan(), preview=False, live_consent=consent)

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertTrue(result.executed)
        self.assertEqual("true", result.verification_results[0].evidence["applied"])
        self.assertEqual(
            "old:1", result.verification_results[0].evidence["observed_source_image"]
        )
        state_store.save.assert_called_once_with(_plan())
        factory.assert_called_once_with(_plan())
        deployment.run.assert_awaited_once_with()

    async def test_source_mismatch_blocks_without_downstream_mutation(self) -> None:
        workflow, factory, state_store, _ = _workflow()
        workflow.runtime_observer.observe.side_effect = [_runtime("other:1")]

        result = await workflow.run(
            _plan(),
            preview=False,
            live_consent=LiveConsent(live_flag=True, confirmed=True),
        )

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual(
            "runtime_source_mismatch", result.verification_results[0].evidence["reason"]
        )
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
        workflow, factory, state_store, _ = _workflow(initial="new:1", target="old:1")
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
        state_store.save.assert_not_called()

    async def test_recover_uses_recorded_plan_when_static_compose_still_has_source(
        self,
    ) -> None:
        workflow, factory, state_store, _ = _workflow(initial="new:1", target="old:1")
        state_store.load.return_value = SimpleNamespace(plan=_plan())

        result = await workflow.recover(
            "jenkins",
            "jenkins",
            preview=False,
            live_consent=LiveConsent(live_flag=True, confirmed=True),
        )

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        factory.assert_called_once_with(_plan().rollback_plan)
        state_store.save.assert_not_called()

    async def test_repeated_recovery_never_reverses_the_original_plan_again(
        self,
    ) -> None:
        workflow, factory, state_store, _ = _workflow()
        recorded = SimpleNamespace(plan=_plan())
        state_store.load.side_effect = lambda *_: recorded
        state_store.save.side_effect = lambda plan: setattr(recorded, "plan", plan)
        consent = LiveConsent(live_flag=True, confirmed=True)
        workflow.runtime_observer.observe.side_effect = [
            _runtime("new:1"),
            _runtime("old:1"),
            _runtime("old:1"),
        ]

        await workflow.recover(
            "jenkins", "jenkins", preview=False, live_consent=consent
        )
        await workflow.recover(
            "jenkins", "jenkins", preview=False, live_consent=consent
        )

        self.assertEqual(_plan(), recorded.plan)
        factory.assert_called_once_with(_plan().rollback_plan)
        state_store.save.assert_not_called()

    async def test_completed_rollback_recovery_is_noop(self) -> None:
        workflow, factory, store, _ = _workflow()
        store.load.return_value = SimpleNamespace(plan=_plan())
        workflow.runtime_observer.observe.side_effect = [
            _runtime("old:1", rollout="rollback_completed"),
            _runtime("old:1", rollout="rollback_completed"),
        ]
        for _ in range(2):
            result = await workflow.recover(
                "jenkins", "jenkins", preview=False, live_consent=_consent()
            )
            self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
            self.assertFalse(result.executed)
        factory.assert_not_called()
        store.save.assert_not_called()
        self.assertEqual(_plan(), store.load.return_value.plan)

    async def test_failed_forward_rollout_is_not_a_target_noop(self) -> None:
        workflow, factory, store, _ = _workflow()
        workflow.runtime_observer.observe.side_effect = [
            _runtime("new:1", rollout="rollback_completed")
        ]
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        factory.assert_not_called()
        store.save.assert_not_called()

    async def test_recovery_requires_convergence_despite_rollback_status(self) -> None:
        for observed in (
            _runtime("old:1", rollout="paused"),
            _runtime("old:1", rollout="updating"),
            _runtime("old:1", rollout="rollback_started"),
            _runtime("old:1", rollout="rollback_paused"),
            _runtime("old:1", task_image="new:1", rollout="rollback_completed"),
        ):
            with self.subTest(observed=observed):
                workflow, factory, store, _ = _workflow()
                store.load.return_value = SimpleNamespace(plan=_plan())
                workflow.runtime_observer.observe.side_effect = [observed] * 3
                result = await workflow.recover(
                    "jenkins", "jenkins", preview=False, live_consent=_consent()
                )
                self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
                self.assertTrue(result.executed)
                factory.assert_called_once_with(_plan().rollback_plan)
                store.save.assert_not_called()

    async def test_apply_uses_running_source_even_when_compose_is_stale(self) -> None:
        workflow, factory, _, _ = _workflow()
        workflow.compose_repository.get_services_of.return_value = (
            ComposeServiceDefinition(name="jenkins", image_ref="stale:1"),
        )
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        factory.assert_called_once()
        self.assertEqual(
            VerificationEvidenceScope.LIVE,
            result.verification_results[0].evidence_scope,
        )

    async def test_repeating_completed_update_is_observed_noop(self) -> None:
        workflow, factory, store, _ = _workflow(initial="new:1")
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(result.executed)
        factory.assert_not_called()
        store.save.assert_not_called()

    async def test_missing_or_failed_observation_blocks_without_mutation(self) -> None:
        for observation in (
            None,
            UpdateObservationError("unavailable"),
            ValueError("malformed"),
        ):
            with self.subTest(observation=observation):
                workflow, factory, store, _ = _workflow()
                if observation is None:
                    workflow.runtime_observer = None
                else:
                    workflow.runtime_observer.observe.side_effect = observation
                result = await workflow.run(
                    _plan(), preview=False, live_consent=_consent()
                )
                self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
                self.assertFalse(result.executed)
                factory.assert_not_called()
                store.save.assert_not_called()

    async def test_observation_timeout_blocks_without_mutation(self) -> None:
        workflow, factory, store, _ = _workflow()

        async def stalled(*_):
            await asyncio.sleep(10)

        workflow.runtime_observer.observe.side_effect = stalled
        workflow.observation_timeout_seconds = 0.001
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        factory.assert_not_called()
        store.save.assert_not_called()

    async def test_task_rollout_must_converge_after_deployment_completes(self) -> None:
        workflow, _, _, _ = _workflow()
        workflow.runtime_observer.observe.side_effect = [
            _runtime(),
            _runtime("new:1", task_image="old:1", rollout="updating"),
            _runtime("new:1"),
        ]
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(3, workflow.runtime_observer.observe.await_count)

    async def test_stale_mixed_or_failed_tasks_do_not_pass_on_replica_count(
        self,
    ) -> None:
        mixed = replace(
            _runtime("new:1"),
            desired_replicas=2,
            tasks=(
                UpdateTaskObservation("one", "new:1", "running", "running"),
                UpdateTaskObservation("two", "old:1", "running", "running"),
            ),
        )
        for stalled in (
            _runtime("new:1", task_image="old:1"),
            mixed,
            _runtime("new:1", state="failed"),
            _runtime("new:1", rollout="updating"),
        ):
            with self.subTest(stalled=stalled):
                workflow, _, store, _ = _workflow()
                workflow.runtime_observer.observe.side_effect = [
                    _runtime(),
                    stalled,
                    stalled,
                ]
                result = await workflow.run(
                    _plan(), preview=False, live_consent=_consent()
                )
                self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
                self.assertTrue(result.executed)
                store.save.assert_called_once_with(_plan())

    async def test_failed_rollout_or_replaced_service_stops_verification(self) -> None:
        for observed in (
            _runtime("new:1", rollout="paused"),
            _runtime("old:1", rollout="rollback_completed"),
            _runtime("new:1", rollout="rollback_completed"),
            replace(_runtime("new:1"), service_id="replacement"),
        ):
            with self.subTest(observed=observed):
                workflow, _, _, _ = _workflow()
                workflow.runtime_observer.observe.side_effect = [_runtime(), observed]
                result = await workflow.run(
                    _plan(), preview=False, live_consent=_consent()
                )
                self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
                self.assertEqual(2, workflow.runtime_observer.observe.await_count)

    async def test_failed_post_apply_observation_is_failed_verification(self) -> None:
        workflow, _, store, _ = _workflow()
        workflow.runtime_observer.observe.side_effect = [
            _runtime(),
            UpdateObservationError("failed"),
        ]
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
        self.assertTrue(result.executed)
        store.save.assert_called_once_with(_plan())

    async def test_unreadable_or_unwritable_state_blocks_before_deployment(
        self,
    ) -> None:
        for method in ("save", "load"):
            with self.subTest(method=method):
                workflow, factory, store, _ = _workflow()
                getattr(store, method).side_effect = OSError("disk unavailable")
                result = await workflow.run(
                    _plan(), preview=False, live_consent=_consent()
                )
                self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
                factory.assert_not_called()

    async def test_unrelated_unresolved_state_is_not_overwritten(self) -> None:
        workflow, factory, store, _ = _workflow()
        store.load.return_value = SimpleNamespace(
            plan=replace(_plan(), source_image="other:1", target_image="other:2")
        )
        result = await workflow.run(_plan(), preview=False, live_consent=_consent())
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        store.save.assert_not_called()
        factory.assert_not_called()

    async def test_recovery_failure_preserves_original_and_retry_reuses_it(
        self,
    ) -> None:
        workflow, factory, store, deployment = _workflow(
            initial="new:1", target="old:1"
        )
        store.load.return_value = SimpleNamespace(plan=_plan())
        deployment.run.side_effect = [
            RuntimeError("interrupted"),
            SimpleNamespace(
                status=DeploymentWorkflowStatus.COMPLETED,
                verification_results=(),
            ),
        ]
        workflow.runtime_observer.observe.side_effect = [
            _runtime("new:1"),
            _runtime("new:1"),
            _runtime("old:1"),
        ]
        failed = await workflow.recover(
            "jenkins", "jenkins", preview=False, live_consent=_consent()
        )
        retry = await workflow.recover(
            "jenkins", "jenkins", preview=False, live_consent=_consent()
        )
        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, failed.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, retry.status)
        self.assertTrue(
            all(
                call.args[0] == _plan().rollback_plan for call in factory.call_args_list
            )
        )
        store.save.assert_not_called()

    async def test_recovery_repairs_partial_known_transition_but_rejects_foreign_image(
        self,
    ) -> None:
        for image, expected in (
            ("old:1", PlatformWorkflowStatus.COMPLETED),
            ("unrelated:1", PlatformWorkflowStatus.BLOCKED),
        ):
            with self.subTest(image=image):
                workflow, factory, store, _ = _workflow()
                store.load.return_value = SimpleNamespace(plan=_plan())
                workflow.runtime_observer.observe.side_effect = [
                    _runtime("new:1", task_image=image, rollout="paused"),
                    _runtime("old:1"),
                ]
                result = await workflow.recover(
                    "jenkins", "jenkins", preview=False, live_consent=_consent()
                )
                self.assertEqual(expected, result.status)
                if expected is PlatformWorkflowStatus.BLOCKED:
                    factory.assert_not_called()
                store.save.assert_not_called()

    async def test_recovery_preview_is_static_and_does_not_overwrite_state(
        self,
    ) -> None:
        workflow, factory, store, _ = _workflow()
        store.load.return_value = SimpleNamespace(plan=_plan())
        result = await workflow.recover(
            "jenkins", "jenkins", preview=True, live_consent=None
        )
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        workflow.runtime_observer.observe.assert_not_awaited()
        store.save.assert_not_called()
        factory.assert_not_called()

    async def test_recovery_refuses_state_for_a_different_service(self) -> None:
        workflow, factory, store, _ = _workflow()
        store.load.return_value = SimpleNamespace(
            plan=replace(_plan(), service_name="other")
        )
        result = await workflow.recover(
            "jenkins", "jenkins", preview=False, live_consent=_consent()
        )
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        factory.assert_not_called()
        workflow.runtime_observer.observe.assert_not_awaited()

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
        self.assertEqual(
            "state_not_found", result.verification_results[0].evidence["reason"]
        )
        factory.assert_not_called()


def _consent():
    return LiveConsent(live_flag=True, confirmed=True)
