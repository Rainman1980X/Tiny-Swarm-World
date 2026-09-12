from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from tiny_swarm_world.application.ports.repositories.port_compose_file_repository import (
    PortComposeFileRepository,
)
from tiny_swarm_world.application.ports.update import PortUpdateStateStore
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
from tiny_swarm_world.domain.update import ClassicUpdatePlan


class _DeploymentWorkflowFactory(Protocol):
    def __call__(self, plan: ClassicUpdatePlan) -> DeploymentApplyWorkflow:
        ...


class ClassicUpdateWorkflow:
    """Validate and execute one explicit, reversible Classic update."""

    semantics = PLATFORM_WORKFLOW_TAXONOMY[PlatformWorkflowKind.UPDATE]

    def __init__(
        self,
        compose_repository: PortComposeFileRepository,
        deployment_workflow_factory: _DeploymentWorkflowFactory,
        state_store: PortUpdateStateStore,
    ):
        self.compose_repository = compose_repository
        self.deployment_workflow_factory = deployment_workflow_factory
        self.state_store = state_store

    async def run(
        self,
        plan: ClassicUpdatePlan,
        *,
        preview: bool,
        live_consent: LiveConsent | None,
    ) -> PlatformWorkflowResult:
        current = self._current_service(plan)
        if isinstance(current, PlatformWorkflowResult):
            return current
        if current.image_ref != plan.source_image:
            return self._blocked(
                plan,
                "source image does not match the currently configured image; no mutation was started",
                {"current_image": current.image_ref, "reason": "source_mismatch"},
            )

        preview_result = self._verification(
            plan,
            status=VerificationStatus.VERIFIED,
            message="Classic update transition is valid and ready for preview or apply.",
            evidence={
                "phase": "pre_apply",
                "current_image": current.image_ref,
                "from_image": plan.source_image,
                "to_image": plan.target_image,
                "mutation": "planned",
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
                        evidence={"phase": "pre_apply", "reason": "live_consent_missing"},
                    ),
                ),
            )

        self.state_store.save(plan)
        deployment_result = await self.deployment_workflow_factory(plan).run()
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
        return PlatformWorkflowResult.completed(
            self.semantics,
            executed=True,
            verification_results=(
                preview_result,
                self._verification(
                    plan,
                    status=VerificationStatus.VERIFIED,
                    message="Classic update applied through the deployment port.",
                    evidence={
                        "phase": "apply",
                        "applied": "true",
                        "from_image": plan.source_image,
                        "to_image": plan.target_image,
                        "rollback_state": "recorded",
                    },
                ),
                *deployment_result.verification_results,
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
        return await self.run(
            state.plan.rollback_plan,
            preview=preview,
            live_consent=live_consent,
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
        service = next((item for item in services if item.name == plan.service_name), None)
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
            (self._verification(plan, status=VerificationStatus.BLOCKED, message=message, evidence=evidence),),
        )

    @staticmethod
    def _verification(
        plan: ClassicUpdatePlan,
        *,
        status: VerificationStatus,
        message: str,
        evidence: Mapping[str, str],
    ) -> VerificationResult:
        return ClassicUpdateWorkflow._verification_for_target(
            plan.target_id,
            status=status,
            message=message,
            evidence=evidence,
        )

    @staticmethod
    def _verification_for_target(
        target_id: str,
        *,
        status: VerificationStatus,
        message: str,
        evidence: Mapping[str, str],
    ) -> VerificationResult:
        return VerificationResult(
            target_id=target_id,
            status=status,
            message=message,
            evidence=evidence,
            evidence_scope=VerificationEvidenceScope.STATIC,
        )
