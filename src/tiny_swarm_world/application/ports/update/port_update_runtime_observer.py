from __future__ import annotations

from abc import ABC, abstractmethod

from tiny_swarm_world.domain.update import UpdateRuntimeObservation


class UpdateObservationError(RuntimeError):
    """Runtime state could not be observed completely and safely."""


class PortUpdateRuntimeObserver(ABC):
    @abstractmethod
    async def observe(
        self, stack_name: str, service_name: str
    ) -> UpdateRuntimeObservation:
        """Read service and task state without deploying or altering the runtime."""
