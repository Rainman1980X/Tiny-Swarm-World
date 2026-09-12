"""Check operator-owned host prerequisites before deployment mutations."""

from tiny_swarm_world.application.ports.host import PortHostPreparation
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus


class VerifyHostPrerequisites:
    verification_target_id = "deployment:host-kernel-prerequisites"

    def __init__(self, host: PortHostPreparation | None) -> None:
        self.host = host

    def verify(self) -> VerificationResult:
        if self.host is None:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.BLOCKED,
                message="Deployment requires a verified supported host environment.",
                evidence={"phase": "prerequisite", "classification": "host_environment_unverified"},
            )
        result = self.host.verify()
        ready = result.succeeded and result.verified
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.VERIFIED if ready else VerificationStatus.BLOCKED,
            message=(
                "Host kernel prerequisites are active."
                if ready else
                "Host kernel prerequisites are not ready. Verify persistent br_netfilter "
                "loading and bridge sysctls on the native host before restarting Docker "
                "in the managed nodes and retrying deployment."
            ),
            evidence={
                "phase": "prerequisite",
                "classification": "verified" if ready else "host_kernel_prerequisites_missing",
                **dict(result.evidence),
            },
        )
