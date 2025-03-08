from abc import abstractmethod, ABC
from pathlib import Path


class PathStrategy(ABC):
    """Abstract base class for OS-specific path strategies."""

    @abstractmethod
    def normalize(self, path: Path) -> str:
        """Returns a normalized absolute path."""
        pass