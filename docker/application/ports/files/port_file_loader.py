from abc import ABC, abstractmethod
from typing import Any

class PortFileLoader(ABC):

    @property
    @abstractmethod
    def path(self) -> str:
        """Returns the path to the file."""
        pass

    @abstractmethod
    def load(self) -> Any:
        """Loads the configuration and returns it as a dictionary."""
        pass
