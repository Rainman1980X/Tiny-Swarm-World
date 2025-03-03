from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PortFileSaver(ABC):
    @property
    @abstractmethod
    def path(self) -> Path:
        """Returns the path to the file."""
        pass

    @abstractmethod
    def save(self, data: Any) -> None:
        """Saves the configuration to the file."""