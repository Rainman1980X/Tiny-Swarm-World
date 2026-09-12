from __future__ import annotations

from abc import ABC, abstractmethod

from tiny_swarm_world.domain.update import ClassicUpdatePlan, ClassicUpdateState


class PortUpdateStateStore(ABC):
    @abstractmethod
    def save(self, plan: ClassicUpdatePlan) -> ClassicUpdateState:
        pass

    @abstractmethod
    def load(self, stack_name: str, service_name: str) -> ClassicUpdateState | None:
        pass
