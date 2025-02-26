from abc import ABC, abstractmethod


class PortCommandRunner(ABC):

    def __init__(self):
        self.status = {
            "current_step": "Initialized",
            "result": "Pending",
        }
    @abstractmethod
    async def run(self, command: str) -> str:
        pass
