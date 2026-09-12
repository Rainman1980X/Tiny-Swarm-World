from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Protocol

from tiny_swarm_world.application.ports.repositories.port_compose_file_repository import (
    PortComposeFileRepository,
)
from tiny_swarm_world.application.ports.update import (
    PortUpdateStateStore,
    PortUpdateRuntimeObserver,
    UpdateObservationError,
    UpdateObservationChanged,
)
from tiny_swarm_world.application.services.deployment.workflows import (
    DeploymentApplyWorkflow,
    DeploymentWorkflowStatus,
)
from tiny_swarm_world.application.services.platform.workflow.results import (
    PlatformWorkflowResult,
)
from tiny_swarm_world.application.services.platform.workflow.semantics import (
    PLATFORM_WORKFLOW_TAXONOMY,
)
from tiny_swarm_world.application.services.platform.workflow.types import (
    PlatformWorkflowKind,
    PlatformWorkflowStatus,
)
from tiny_swarm_world.domain.deployment import ComposeServiceDefinition
from tiny_swarm_world.domain.inventory import (
    VerificationEvidenceScope,
    VerificationResult,
    VerificationStatus,
)
from tiny_swarm_world.domain.preflight import LiveConsent
from tiny_swarm_world.domain.update import ClassicUpdatePlan, UpdateRuntimeObservation


class _DeploymentWorkflowFactory(Protocol):
    def __call__(self, plan: ClassicUpdatePlan) -> DeploymentApplyWorkflow: ...


class ClassicUpdateWorkflow:
    """Validate and execute one explicit, reversible Classic update."""

    semantics = PLATFORM_WORKFLOW_TAXONOMY[PlatformWorkflowKind.UPDATE]

    def __init__(
        self,
        compose_repository: PortComposeFileRepository,
        deployment_workflow_factory: _DeploymentWorkflowFactory,
        state_store: PortUpdateStateStore,
        runtime_observer: PortUpdateRuntimeObserver | None = None,
        *,
        verification_attempts: int = 30,
        poll_interval_seconds: float = 2.0,
        observation_timeout_seconds: float = 10.0,
    ):
        if (
            verification_attempts < 1
            or poll_interval_seconds < 0
            or observation_timeout_seconds <= 0
        ):
            raise ValueError(
                "Update observation bounds must be positive (poll interval may be zero)."
            )
        self.compose_repository = compose_repository
        self.deployment_workflow_factory = deployment_workflow_factory
        self.state_store = state_store
        self.runtime_observer = runtime_observer
        self.verification_attempts = verification_attempts
        self.poll_interval_seconds = poll_interval_seconds
        self.observation_timeout_seconds = observation_timeout_seconds

    async def run(
        self,
        plan: ClassicUpdatePlan,
        *,
        preview: bool,
        live_consent: LiveConsent | None,
    ) -> PlatformWorkflowResult:
        return await self._run(
            plan, preview=preview, live_consent=live_consent, recovery=False
        )

    async def _run(
        self,
        plan: ClassicUpdatePlan,
        *,
        preview: bool,
        live_consent: LiveConsent | None,
        recovery: bool,
    ) -> PlatformWorkflowResult:
        current = self._current_service(plan)
        if isinstance(current, PlatformWorkflowResult):
            return current
        preview_result = self._verification(
            plan,
            status=VerificationStatus.VERIFIED,
            message="Static update preview; runtime qualification is required before apply.",
            evidence={
                "phase": "pre_apply",
                "current_image": current.image_ref,
                "from_image": plan.source_image,
                "to_image": plan.target_image,
                "mutation": "planned",
                "runtime_observed": "false",
            },
        )
        if preview:
            return PlatformWorkflowResult.completed(
                self.semantics,
                executed=False,
                verification_results=(preview_result,),
            )
        if live_consent is None or not live_consent.accepted:
            return PlatformWorkflowResult(
                kind=self.semantics.kind,
                status=PlatformWorkflowStatus.REFUSED,
                message="platform update refused because live infrastructure consent is incomplete.",
                executed=False,
                verification_results=(
                    self._verification(
                        plan,
                        status=VerificationStatus.REFUSED,
                        message="Live consent is required before an update can mutate infrastructure.",
                        evidence={
                            "phase": "pre_apply",
                            "reason": "live_consent_missing",
                        },
                    ),
                ),
            )

        try:
            observed = await self._observe(plan)
        except UpdateObservationError:
            return self._blocked(
                plan,
                "Runtime observation is unavailable; no mutation was started.",
                {"reason": "runtime_observation_unavailable"},
            )
        if observed.converged(plan.target_image, allow_completed_rollback=recovery):
            return self._runtime_completed(
                plan, observed, executed=False, recovery=recovery
            )
        qualified = (
            observed.belongs_to_transition(plan.source_image, plan.target_image)
            if recovery
            else observed.converged(plan.source_image)
        )
        if not qualified:
            return self._blocked(
                plan,
                "Runtime image or rollout does not qualify for this transition; no mutation was started.",
                {"reason": "runtime_source_mismatch", **observed.to_evidence()},
            )
        if not recovery:
            try:
                previous = self.state_store.load(plan.stack_name, plan.service_name)
                if previous is not None and previous.plan != plan:
                    if not (
                        observed.converged(previous.plan.source_image)
                        or observed.converged(previous.plan.target_image)
                    ):
                        return self._blocked(
                            plan,
                            "Unresolved recovery state belongs to another transition.",
                            {"reason": "unresolved_recovery_state"},
                        )
                if previous is None or previous.plan != plan:
                    self.state_store.save(plan)
            except (OSError, ValueError):
                return self._blocked(
                    plan,
                    "Recovery state could not be preserved; no mutation was started.",
                    {"reason": "state_unavailable"},
                )
        return await self._apply_and_verify(plan, observed, recovery=recovery)

    async def _apply_and_verify(
        self,
        plan: ClassicUpdatePlan,
        before: UpdateRuntimeObservation,
        *,
        recovery: bool,
    ) -> PlatformWorkflowResult:
        try:
            deployment_result = await self.deployment_workflow_factory(plan).run()
        except (OSError, ValueError, RuntimeError):
            return self._runtime_failure(
                plan, "deployment_failed", PlatformWorkflowStatus.FAILED_TO_APPLY
            )
        if deployment_result.status != DeploymentWorkflowStatus.COMPLETED:
            status = {
                DeploymentWorkflowStatus.BLOCKED: PlatformWorkflowStatus.BLOCKED,
                DeploymentWorkflowStatus.FAILED_TO_APPLY: PlatformWorkflowStatus.FAILED_TO_APPLY,
                DeploymentWorkflowStatus.FAILED_TO_PREPARE: PlatformWorkflowStatus.FAILED_TO_APPLY,
                DeploymentWorkflowStatus.FAILED_TO_VERIFY: PlatformWorkflowStatus.FAILED_TO_VERIFY,
            }.get(
                deployment_result.status,
                PlatformWorkflowStatus.FAILED_TO_VERIFY,
            )
            return PlatformWorkflowResult(
                kind=self.semantics.kind,
                status=status,
                message="platform update did not complete its deployment verification.",
                executed=True,
                verification_results=deployment_result.verification_results,
            )
        for attempt in range(self.verification_attempts):
            try:
                observed = await self._observe(plan)
            except UpdateObservationChanged:
                if attempt + 1 == self.verification_attempts:
                    return self._runtime_failure(plan, "runtime_snapshot_unstable")
                await asyncio.sleep(self.poll_interval_seconds)
                continue
            except UpdateObservationError:
                return self._runtime_failure(plan, "runtime_observation_unavailable")
            if observed.service_id != before.service_id:
                return self._runtime_failure(
                    plan, "service_identity_changed", observation=observed
                )
            if observed.converged(plan.target_image, allow_completed_rollback=recovery):
                return self._runtime_completed(
                    plan,
                    observed,
                    executed=True,
                    recovery=recovery,
                    deployment_evidence=deployment_result.verification_results,
                    observed_source_image=before.desired_image,
                    observation_attempts=attempt + 1,
                )
            if observed.rollout_failed:
                return self._runtime_failure(
                    plan, "rollout_failed", observation=observed
                )
            if attempt + 1 < self.verification_attempts:
                await asyncio.sleep(self.poll_interval_seconds)
        return self._runtime_failure(plan, "target_not_converged", observation=observed)

    async def _observe(self, plan: ClassicUpdatePlan) -> UpdateRuntimeObservation:
        if self.runtime_observer is None:
            raise UpdateObservationError("runtime_observer_missing")
        try:
            observed = await asyncio.wait_for(
                self.runtime_observer.observe(plan.stack_name, plan.service_name),
                timeout=self.observation_timeout_seconds,
            )
        except (OSError, ValueError, TimeoutError) as exc:
            raise UpdateObservationError("runtime_observation_unavailable") from exc
        if (
            not isinstance(observed, UpdateRuntimeObservation)
            or observed.stack_name != plan.stack_name
            or observed.service_name != plan.service_name
            or not observed.service_id
        ):
            raise UpdateObservationError("runtime_identity_mismatch")
        return observed

    def _runtime_completed(
        self,
        plan: ClassicUpdatePlan,
        observed: UpdateRuntimeObservation,
        *,
        executed: bool,
        recovery: bool,
        deployment_evidence: tuple[VerificationResult, ...] = (),
        observed_source_image: str | None = None,
        observation_attempts: int = 1,
    ) -> PlatformWorkflowResult:
        return PlatformWorkflowResult.completed(
            self.semantics,
            executed=executed,
            verification_results=(
                self._verification(
                    plan,
                    status=VerificationStatus.VERIFIED,
                    message="Selected service and running tasks converged to the requested image.",
                    evidence={
                        **observed.to_evidence(),
                        "observation_attempts": str(observation_attempts),
                        "phase": "recovery" if recovery else "apply",
                        "from_image": plan.source_image,
                        "to_image": plan.target_image,
                        "mutation": "applied" if executed else "not_needed",
                        "applied": "true" if executed else "false",
                        "observed_source_image": observed_source_image
                        or observed.desired_image,
                        "rollback_state": "original_preserved"
                        if recovery
                        else "unchanged"
                        if not executed
                        else "recorded",
                    },
                    evidence_scope=VerificationEvidenceScope.LIVE,
                ),
                *deployment_evidence,
            ),
        )

    def _runtime_failure(
        self,
        plan: ClassicUpdatePlan,
        reason: str,
        status: PlatformWorkflowStatus = PlatformWorkflowStatus.FAILED_TO_VERIFY,
        *,
        observation: UpdateRuntimeObservation | None = None,
    ) -> PlatformWorkflowResult:
        message = "Update did not establish target convergence; original recovery state is retained."
        return PlatformWorkflowResult(
            kind=self.semantics.kind,
            status=status,
            message=message,
            executed=True,
            verification_results=(
                self._verification(
                    plan,
                    status=(
                        VerificationStatus.FAILED_TO_APPLY
                        if status is PlatformWorkflowStatus.FAILED_TO_APPLY
                        else VerificationStatus.FAILED_TO_VERIFY
                    ),
                    message=message,
                    evidence={
                        "phase": "post_apply",
                        "reason": reason,
                        "rollback_state": "retained",
                        **(observation.to_evidence() if observation else {}),
                    },
                    evidence_scope=VerificationEvidenceScope.LIVE,
                ),
            ),
        )

    async def recover(
        self,
        stack_name: str,
        service_name: str,
        *,
        preview: bool,
        live_consent: LiveConsent | None,
    ) -> PlatformWorkflowResult:
        try:
            state = self.state_store.load(stack_name, service_name)
        except (OSError, ValueError):
            state = None
        if state is None:
            message = (
                "no rollback state is available for the selected stack/service; "
                "no mutation was started"
            )
            target_id = f"update:{stack_name}:{service_name}:recovery"
            return PlatformWorkflowResult.blocked(
                self.semantics,
                message,
                (
                    self._verification_for_target(
                        target_id,
                        status=VerificationStatus.BLOCKED,
                        message=message,
                        evidence={"phase": "recovery", "reason": "state_not_found"},
                    ),
                ),
            )
        if (
            state.plan.stack_name != stack_name
            or state.plan.service_name != service_name
        ):
            return self._blocked(
                state.plan,
                "Recovery state belongs to another service.",
                {"reason": "state_identity_mismatch"},
            )
        return await self._run(
            state.plan.rollback_plan,
            preview=preview,
            live_consent=live_consent,
            recovery=True,
        )

    def _current_service(
        self,
        plan: ClassicUpdatePlan,
    ) -> ComposeServiceDefinition | PlatformWorkflowResult:
        try:
            services = self.compose_repository.get_services_of(plan.stack_name)
        except (OSError, ValueError) as exc:
            return self._blocked(
                plan,
                "update preview could not inspect the selected stack; no mutation was started",
                {"reason": exc.__class__.__name__},
            )
        service = next(
            (item for item in services if item.name == plan.service_name), None
        )
        if service is None:
            return self._blocked(
                plan,
                "selected service is not part of the selected stack; no mutation was started",
                {"reason": "service_not_found"},
            )
        return service

    def _blocked(
        self,
        plan: ClassicUpdatePlan,
        message: str,
        evidence: Mapping[str, str],
    ) -> PlatformWorkflowResult:
        return PlatformWorkflowResult.blocked(
            self.semantics,
            message,
            (
                self._verification(
                    plan,
                    status=VerificationStatus.BLOCKED,
                    message=message,
                    evidence=evidence,
                ),
            ),
        )

    @staticmethod
    def _verification(
        plan: ClassicUpdatePlan,
        *,
        status: VerificationStatus,
        message: str,
        evidence: Mapping[str, str],
        evidence_scope: VerificationEvidenceScope = VerificationEvidenceScope.STATIC,
    ) -> VerificationResult:
        return ClassicUpdateWorkflow._verification_for_target(
            plan.target_id,
            status=status,
            message=message,
            evidence=evidence,
            evidence_scope=evidence_scope,
        )

    @staticmethod
    def _verification_for_target(
        target_id: str,
        *,
        status: VerificationStatus,
        message: str,
        evidence: Mapping[str, str],
        evidence_scope: VerificationEvidenceScope = VerificationEvidenceScope.STATIC,
    ) -> VerificationResult:
        return VerificationResult(
            target_id=target_id,
            status=status,
            message=message,
            evidence=evidence,
            evidence_scope=evidence_scope,
        )
