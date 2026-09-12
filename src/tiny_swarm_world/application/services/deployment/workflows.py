from __future__ import annotations

import asyncio
import inspect
import logging
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from tiny_swarm_world.application.ports.clients.port_portainer_admin_client import (
    PortainerAdminInitializationRejected,
)
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus
from tiny_swarm_world.domain.inventory.safe_text import validate_message_text


class DeploymentWorkflowKind(str, Enum):
    BOOTSTRAP = "bootstrap"
    APPLY = "apply"
    VERIFY = "verify"


class DeploymentWorkflowStatus(str, Enum):
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED_TO_APPLY = "failed_to_apply"
    FAILED_TO_PREPARE = "failed_to_prepare"
    FAILED_TO_VERIFY = "failed_to_verify"
    TIMED_OUT = "timed_out"


class DeploymentApplyStep(Protocol):
    def run(self) -> object:
        # Protocol declaration; concrete steps apply stack changes.
        pass

    def verify(self) -> object:
        # Protocol declaration; concrete steps report post-apply evidence.
        pass


class DeploymentVerifyCheck(Protocol):
    def verify(self) -> object:
        # Protocol declaration; concrete checks inspect deployed state.
        pass


class DeploymentPreApplyCheck(Protocol):
    def verify(self) -> object:
        # Protocol declaration; concrete checks enforce pre-apply readiness.
        pass


class DeploymentPreApplyStep(Protocol):
    def run(self) -> object:
        # Protocol declaration; concrete steps prepare pre-apply inputs.
        pass


DeploymentWorkflowComponent = (
    DeploymentApplyStep | DeploymentVerifyCheck | DeploymentPreApplyCheck | DeploymentPreApplyStep
)


@dataclass(frozen=True)
class DeploymentWorkflowResult:
    kind: DeploymentWorkflowKind
    status: DeploymentWorkflowStatus
    message: str
    reason: str
    executed: bool = False
    verification_results: tuple[VerificationResult, ...] = ()

    @property
    def workflow_name(self) -> str:
        return f"deployment {self.kind.value}"

    def to_dict(self) -> dict[str, object]:
        return {
            "executed": self.executed,
            "message": self.message,
            "reason": self.reason,
            "status": self.status.value,
            "verification_results": [
                verification.to_dict() for verification in self.verification_results
            ],
            "workflow": self.workflow_name,
        }


DEFAULT_DEPLOYMENT_APPLY_BLOCK_REASON = (
    "Portainer stack changes require command-backed verification and live "
    "operation contracts before apply can run"
)
DEPLOYMENT_APPLY_CONTRACTS_BLOCKED_MESSAGE = (
    "deployment apply is blocked until stack deployment contracts are wired."
)
VERIFICATION_EVIDENCE_MISSING_MESSAGE = "Verification evidence is missing."
DIAGNOSTIC_PAYLOAD_REDACTED = "Diagnostic payload redacted."
UNSAFE_EXCEPTION_DETAIL_TERMS = (
    "authorization",
    "credential",
    "password",
    "payload",
    "response body",
    "secret",
    "stderr",
    "stdout",
    "token",
)


class DeploymentApplyWorkflow:
    def __init__(
        self,
        steps: Sequence[DeploymentApplyStep] = (),
        pre_apply_steps: Sequence[DeploymentPreApplyStep] = (),
        pre_apply_checks: Sequence[DeploymentPreApplyCheck] = (),
        blocked_reason: str = DEFAULT_DEPLOYMENT_APPLY_BLOCK_REASON,
        kind: DeploymentWorkflowKind = DeploymentWorkflowKind.APPLY,
        prerequisite_checks: Sequence[DeploymentPreApplyCheck] = (),
    ):
        self.steps = tuple(steps)
        self.pre_apply_steps = tuple(pre_apply_steps)
        self.pre_apply_checks = tuple(pre_apply_checks)
        self.prerequisite_checks = tuple(prerequisite_checks)
        self.blocked_reason = blocked_reason
        self.kind = kind
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self) -> DeploymentWorkflowResult:
        if not self.steps:
            return DeploymentWorkflowResult(
                kind=self.kind,
                status=DeploymentWorkflowStatus.BLOCKED,
                message=DEPLOYMENT_APPLY_CONTRACTS_BLOCKED_MESSAGE,
                reason=self.blocked_reason,
            )

        verification_results: list[VerificationResult] = []
        prerequisite_result = await _run_pre_apply_checks(
            self.prerequisite_checks, self.kind, verification_results,
        )
        if prerequisite_result is not None:
            return prerequisite_result
        pre_apply_prepare_result = await _run_pre_apply_steps(
            self.pre_apply_steps,
            self.kind,
            verification_results,
            self.logger,
        )
        if pre_apply_prepare_result is not None:
            return pre_apply_prepare_result

        pre_apply_result = await _run_pre_apply_checks(
            self.pre_apply_checks,
            self.kind,
            verification_results,
        )
        if pre_apply_result is not None:
            return pre_apply_result

        for step in self.steps:
            target_id = _verification_target_id(step, "deployment:apply-step")
            if not _step_has_verification(step):
                blocked_verification = VerificationResult(
                    target_id=target_id,
                    status=VerificationStatus.BLOCKED,
                    message=VERIFICATION_EVIDENCE_MISSING_MESSAGE,
                    evidence={"phase": "pre_apply", "reason": "verify_after_apply_missing"},
                )
                verification_results.append(blocked_verification)
                return DeploymentWorkflowResult(
                    kind=self.kind,
                    status=DeploymentWorkflowStatus.BLOCKED,
                    message=DEPLOYMENT_APPLY_CONTRACTS_BLOCKED_MESSAGE,
                    reason="verify-after-apply contract is missing for deployment apply",
                    verification_results=tuple(verification_results),
                )

            try:
                apply_result = step.run()
                if inspect.isawaitable(apply_result):
                    await apply_result
            except Exception as exc:
                safe_error = _safe_exception_summary(exc)
                self.logger.error(
                    "Failed to apply deployment target '%s'. Error: %s",
                    target_id,
                    safe_error,
                )
                return DeploymentWorkflowResult(
                    kind=self.kind,
                    status=DeploymentWorkflowStatus.FAILED_TO_APPLY,
                    message="deployment apply failed for a configured stack contract.",
                    reason=_apply_failure_reason(target_id, exc, safe_error),
                    executed=True,
                    verification_results=(
                        *verification_results,
                        VerificationResult(
                            target_id=target_id,
                            status=VerificationStatus.FAILED_TO_APPLY,
                            message=f"Apply failed for {target_id}: {safe_error}",
                            evidence=_apply_failure_evidence(exc),
                        ),
                    ),
                )

            verification = await _verify_step(step, target_id)
            verification_results.append(verification)
            if verification.status == VerificationStatus.BLOCKED:
                return DeploymentWorkflowResult(
                    kind=self.kind,
                    status=DeploymentWorkflowStatus.BLOCKED,
                    message=DEPLOYMENT_APPLY_CONTRACTS_BLOCKED_MESSAGE,
                    reason=f"verification is blocked for {target_id}",
                    executed=True,
                    verification_results=tuple(verification_results),
                )
            if verification.status != VerificationStatus.VERIFIED:
                return DeploymentWorkflowResult(
                    kind=self.kind,
                    status=DeploymentWorkflowStatus.FAILED_TO_VERIFY,
                    message="deployment apply failed verification for a configured stack contract.",
                    reason=f"verification failed for {target_id}",
                    executed=True,
                    verification_results=tuple(verification_results),
                )

        return DeploymentWorkflowResult(
            kind=self.kind,
            status=DeploymentWorkflowStatus.COMPLETED,
            message="deployment apply completed for configured stack contracts.",
            reason="configured stack contracts applied and verified through deployment ports",
            executed=True,
            verification_results=tuple(verification_results),
        )


class DeploymentVerifyWorkflow:
    def __init__(
        self,
        checks: Sequence[DeploymentVerifyCheck] = (),
        *,
        timeout_seconds: float | None = None,
    ):
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("Deployment verify timeout must be positive.")
        self.checks = tuple(checks)
        self.timeout_seconds = timeout_seconds
        self._last_verification_results: list[VerificationResult] = []

    async def run(self) -> DeploymentWorkflowResult:
        if not self.checks:
            return DeploymentWorkflowResult(
                kind=DeploymentWorkflowKind.VERIFY,
                status=DeploymentWorkflowStatus.BLOCKED,
                message="deployment verify is blocked until stack verification contracts are wired.",
                reason=(
                    "stack and service observed-state verification is not implemented through "
                    "deployment ports"
                ),
            )

        self._last_verification_results = []
        try:
            if self.timeout_seconds is None:
                return await self._run_checks()
            return await asyncio.wait_for(self._run_checks(), self.timeout_seconds)
        except asyncio.TimeoutError:
            return DeploymentWorkflowResult(
                kind=DeploymentWorkflowKind.VERIFY,
                status=DeploymentWorkflowStatus.TIMED_OUT,
                message="deployment verify timed out.",
                reason=(
                    f"deployment verify exceeded its configured timeout of "
                    f"{self.timeout_seconds:g} seconds"
                ),
                verification_results=tuple(self._last_verification_results),
            )

    async def _run_checks(self) -> DeploymentWorkflowResult:
        verification_results: list[VerificationResult] = []
        for check in self.checks:
            target_id = _verification_target_id(check, "deployment:verify-check")
            verification = await _verify_step(check, target_id)
            verification_results.append(verification)
            self._last_verification_results = list(verification_results)
            if verification.status == VerificationStatus.BLOCKED:
                return DeploymentWorkflowResult(
                    kind=DeploymentWorkflowKind.VERIFY,
                    status=DeploymentWorkflowStatus.BLOCKED,
                    message="deployment verify is blocked until stack verification contracts are wired.",
                    reason=f"verification is blocked for {target_id}",
                    verification_results=tuple(verification_results),
                )
            if verification.status != VerificationStatus.VERIFIED:
                return DeploymentWorkflowResult(
                    kind=DeploymentWorkflowKind.VERIFY,
                    status=DeploymentWorkflowStatus.FAILED_TO_VERIFY,
                    message="deployment verify failed for a configured stack contract.",
                    reason=f"verification failed for {target_id}",
                    verification_results=tuple(verification_results),
                )

        return DeploymentWorkflowResult(
            kind=DeploymentWorkflowKind.VERIFY,
            status=DeploymentWorkflowStatus.COMPLETED,
            message="deployment verify completed for configured stack contracts.",
            reason="configured stack contracts verified through deployment ports",
            verification_results=tuple(verification_results),
        )


@dataclass(frozen=True)
class ValidationPlan:
    name: str
    required_targets: tuple[str, ...]
    optional_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("validation plan name must not be empty")
        required_targets = _normalized_target_ids(self.required_targets, "required_targets")
        optional_targets = _normalized_target_ids(self.optional_targets, "optional_targets")
        overlap = sorted(set(required_targets) & set(optional_targets))
        if overlap:
            raise ValueError("validation plan targets must not be both required and optional")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "required_targets", required_targets)
        object.__setattr__(self, "optional_targets", optional_targets)

    def evaluate(
        self,
        evidence: Sequence[VerificationResult],
    ) -> DeploymentWorkflowResult:
        evidence_by_target = {item.target_id: item for item in evidence}
        results: list[VerificationResult] = []
        for target_id in self.required_targets:
            verification = evidence_by_target.get(target_id)
            if verification is None:
                results.append(
                    VerificationResult(
                        target_id=target_id,
                        status=VerificationStatus.FAILED_TO_VERIFY,
                        message="Required validation evidence is missing.",
                        evidence={
                            "phase": "validation",
                            "reason": "required_evidence_missing",
                            "validation_plan": self.name,
                        },
                    )
                )
                continue
            if verification.status == VerificationStatus.VERIFIED and not _has_observed_evidence(
                verification
            ):
                results.append(
                    VerificationResult(
                        target_id=target_id,
                        status=VerificationStatus.FAILED_TO_VERIFY,
                        message="Required validation evidence is not observed runtime evidence.",
                        evidence={
                            "phase": "validation",
                            "reason": "observed_evidence_missing",
                            "validation_plan": self.name,
                        },
                    )
                )
                continue
            results.append(verification)

        for target_id in self.optional_targets:
            verification = evidence_by_target.get(target_id)
            if verification is not None:
                results.append(verification)

        if any(result.status == VerificationStatus.BLOCKED for result in results):
            status = DeploymentWorkflowStatus.BLOCKED
            message = "deployment validation is blocked by observed evidence."
            reason = "validation evidence contains blocked target"
        elif any(result.status != VerificationStatus.VERIFIED for result in results):
            status = DeploymentWorkflowStatus.FAILED_TO_VERIFY
            message = "deployment validation failed for observed evidence."
            reason = "validation evidence missing or failed"
        else:
            status = DeploymentWorkflowStatus.COMPLETED
            message = "deployment validation completed for observed evidence."
            reason = "required validation evidence verified"

        return DeploymentWorkflowResult(
            kind=DeploymentWorkflowKind.VERIFY,
            status=status,
            message=message,
            reason=reason,
            verification_results=tuple(results),
        )


def _normalized_target_ids(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"validation plan {field_name} entries must not be empty")
    duplicates = sorted(
        target_id
        for target_id in set(normalized)
        if normalized.count(target_id) > 1
    )
    if duplicates:
        raise ValueError(f"validation plan {field_name} contains duplicate targets")
    return normalized


def _has_observed_evidence(verification: VerificationResult) -> bool:
    if verification.evidence.get("readiness_observed") == "false":
        return False
    return (
        "replicas" in verification.evidence
        and "required_services" in verification.evidence
        and "stack_name" in verification.evidence
    )


def _step_has_verification(step: DeploymentApplyStep | DeploymentVerifyCheck) -> bool:
    return callable(getattr(step, "verify", None))


def _safe_exception_summary(exc: Exception) -> str:
    status_code = getattr(exc, "status_code", None)
    safe_detail = _safe_exception_detail(exc)
    detail = safe_detail or DIAGNOSTIC_PAYLOAD_REDACTED
    if status_code is not None:
        return f"{exc.__class__.__name__} HTTP {status_code}. {detail}"
    return f"{exc.__class__.__name__}. {detail}"


def _safe_exception_detail(exc: Exception) -> str:
    detail = str(exc).strip()
    if not detail or detail == exc.__class__.__name__:
        return ""
    normalized_detail = detail.casefold()
    if any(term in normalized_detail for term in UNSAFE_EXCEPTION_DETAIL_TERMS):
        return ""
    detail = textwrap.shorten(detail, width=180, placeholder="...")
    try:
        validate_message_text("exception_summary", detail)
    except ValueError:
        return ""
    return detail


def _apply_failure_reason(target_id: str, _exc: Exception, safe_error: str) -> str:
    return f"apply failed for {target_id}: {safe_error}"


def _apply_failure_evidence(exc: Exception) -> dict[str, str]:
    evidence = {
        "phase": "apply",
        "classification": "deployment_apply_failed",
        "failure_class": exc.__class__.__name__,
        "remediation_hint": "Inspect the deployment target readiness and rerun the idempotent setup after correcting the target-specific blocker.",
    }
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        evidence["diagnostic"] = f"http_status_{status_code}"
    reason = getattr(exc, "reason", None)
    if isinstance(reason, str) and reason:
        evidence["failure_reason"] = reason
    if isinstance(exc, PortainerAdminInitializationRejected):
        evidence["operator_action"] = (
            "Check configured Portainer admin access value or reset existing "
            "Portainer state before rerunning setup."
        )
    return evidence


def _verification_target_id(
    step: DeploymentWorkflowComponent,
    fallback: str,
) -> str:
    target_id = getattr(step, "verification_target_id", "")
    if target_id:
        return str(target_id)
    deployment_target_id = getattr(step, "deployment_target_id", "")
    if deployment_target_id:
        return str(deployment_target_id)
    return fallback


async def _run_pre_apply_steps(
    steps: Sequence[DeploymentPreApplyStep],
    kind: DeploymentWorkflowKind,
    verification_results: list[VerificationResult],
    logger: logging.Logger,
) -> DeploymentWorkflowResult | None:
    for step in steps:
        target_id = _verification_target_id(step, "deployment:pre-apply-step")
        try:
            prepare_result = step.run()
            if inspect.isawaitable(prepare_result):
                await prepare_result
        except Exception as exc:
            safe_error = _safe_exception_summary(exc)
            logger.error(
                "Failed to prepare deployment input '%s'. Error: %s",
                target_id,
                safe_error,
            )
            verification_results.append(
                VerificationResult(
                    target_id=target_id,
                    status=VerificationStatus.FAILED_TO_APPLY,
                    message=f"Pre-apply preparation failed for {target_id}: {safe_error}",
                    evidence={
                        "phase": "pre_apply",
                        "failure_class": exc.__class__.__name__,
                    },
                )
            )
            return DeploymentWorkflowResult(
                kind=kind,
                status=DeploymentWorkflowStatus.FAILED_TO_PREPARE,
                message="deployment prepare failed for a configured pre-apply contract.",
                reason=f"pre-apply prepare failed with {exc.__class__.__name__}",
                executed=True,
                verification_results=tuple(verification_results),
            )
    return None


async def _run_pre_apply_checks(
    checks: Sequence[DeploymentPreApplyCheck],
    kind: DeploymentWorkflowKind,
    verification_results: list[VerificationResult],
) -> DeploymentWorkflowResult | None:
    for check in checks:
        target_id = _verification_target_id(check, "deployment:pre-apply-check")
        verification = await _verify_step(check, target_id)
        verification_results.append(verification)
        if verification.status == VerificationStatus.BLOCKED:
            return DeploymentWorkflowResult(
                kind=kind,
                status=DeploymentWorkflowStatus.BLOCKED,
                message="deployment apply is blocked by pre-apply verification.",
                reason=f"pre-apply verification is blocked for {target_id}",
                verification_results=tuple(verification_results),
            )
        if verification.status != VerificationStatus.VERIFIED:
            return DeploymentWorkflowResult(
                kind=kind,
                status=DeploymentWorkflowStatus.FAILED_TO_VERIFY,
                message="deployment apply failed pre-apply verification.",
                reason=f"pre-apply verification failed for {target_id}",
                verification_results=tuple(verification_results),
            )
    return None


async def _verify_step(
    step: DeploymentWorkflowComponent,
    target_id: str,
) -> VerificationResult:
    verify = getattr(step, "verify", None)
    if not callable(verify):
        return VerificationResult(
            target_id=target_id,
            status=VerificationStatus.BLOCKED,
            message=VERIFICATION_EVIDENCE_MISSING_MESSAGE,
            evidence={"phase": "verify"},
        )
    try:
        async_verify = getattr(step, "verify_async", None)
        verification_output = (
            async_verify() if callable(async_verify) else verify()
        )
        if inspect.isawaitable(verification_output):
            verification_output = await verification_output
    except Exception as exc:
        return VerificationResult(
            target_id=target_id,
            status=VerificationStatus.FAILED_TO_VERIFY,
            message=f"Verification failed for {target_id}: {exc.__class__.__name__}",
            evidence={"phase": "verify"},
        )
    if isinstance(verification_output, VerificationResult):
        return verification_output
    return VerificationResult(
        target_id=target_id,
        status=VerificationStatus.BLOCKED,
        message=VERIFICATION_EVIDENCE_MISSING_MESSAGE,
        evidence={"phase": "verify"},
    )
