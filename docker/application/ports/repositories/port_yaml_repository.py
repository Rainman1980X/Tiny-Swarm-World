from abc import ABC, abstractmethod
from typing import Any


class PortYamlRepository(ABC):

    @abstractmethod
    def create(self, data) -> Any:
        pass

    @abstractmethod
    def load(self, file_path: str) -> Any:
        pass

    @abstractmethod
    def save(self, file_path: str = None) -> None:
        pass