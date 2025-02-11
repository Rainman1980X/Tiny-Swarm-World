from abc import ABC, abstractmethod


class CommandRunner(ABC):
    @abstractmethod
    def run(self, command: str) -> str:
        pass
