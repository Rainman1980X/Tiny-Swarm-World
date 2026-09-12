from __future__ import annotations

from enum import Enum


class PlatformWorkflowKind(str, Enum):
    INIT = "init"
    RECONCILE = "reconcile"
    EXPOSE = "expose"
    REPAIR_LXC_PROXY_DRIFT = "repair-lxc-proxy-drift"
    RESET = "reset"
    DESTROY = "destroy"
    VERIFY = "verify"
    UPDATE = "update"


class PlatformWorkflowStatus(str, Enum):
    COMPLETED = "completed"
    REFUSED = "refused"
    BLOCKED = "blocked"
    FAILED_TO_APPLY = "failed_to_apply"
    FAILED_TO_VERIFY = "failed_to_verify"
