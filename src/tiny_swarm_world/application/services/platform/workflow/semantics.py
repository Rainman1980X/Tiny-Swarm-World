from __future__ import annotations

from dataclasses import dataclass

from tiny_swarm_world.application.services.platform.workflow.constants import (
    DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION,
    RESET_TINY_SWARM_PLATFORM_CONFIRMATION,
)
from tiny_swarm_world.application.services.platform.workflow.types import PlatformWorkflowKind


@dataclass(frozen=True)
class PlatformWorkflowSemantics:
    kind: PlatformWorkflowKind
    mutating: bool
    destructive: bool
    requires_confirmation: bool
    meaning: str
    confirmation_phrase: str | None = None


PLATFORM_WORKFLOW_TAXONOMY = {
    PlatformWorkflowKind.INIT: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.INIT,
        mutating=True,
        destructive=False,
        requires_confirmation=False,
        meaning="create missing managed resources",
    ),
    PlatformWorkflowKind.RECONCILE: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.RECONCILE,
        mutating=True,
        destructive=False,
        requires_confirmation=False,
        meaning="converge existing managed state",
    ),
    PlatformWorkflowKind.EXPOSE: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.EXPOSE,
        mutating=True,
        destructive=False,
        requires_confirmation=False,
        meaning="expose published Swarm service ports through the LXC gateway",
    ),
    PlatformWorkflowKind.REPAIR_LXC_PROXY_DRIFT: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.REPAIR_LXC_PROXY_DRIFT,
        mutating=True,
        destructive=False,
        requires_confirmation=False,
        meaning="remove stale direct LXC proxy devices after profile reconciliation",
    ),
    PlatformWorkflowKind.RESET: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.RESET,
        mutating=True,
        destructive=True,
        requires_confirmation=True,
        meaning="explicitly reinitialize managed resources",
        confirmation_phrase=RESET_TINY_SWARM_PLATFORM_CONFIRMATION,
    ),
    PlatformWorkflowKind.DESTROY: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.DESTROY,
        mutating=True,
        destructive=True,
        requires_confirmation=True,
        meaning="explicitly tear down managed resources",
        confirmation_phrase=DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION,
    ),
    PlatformWorkflowKind.VERIFY: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.VERIFY,
        mutating=False,
        destructive=False,
        requires_confirmation=False,
        meaning="inspect current state",
    ),
    PlatformWorkflowKind.UPDATE: PlatformWorkflowSemantics(
        kind=PlatformWorkflowKind.UPDATE,
        mutating=True,
        destructive=False,
        requires_confirmation=False,
        meaning="apply one explicit reversible image transition to an existing stack",
    ),
}
