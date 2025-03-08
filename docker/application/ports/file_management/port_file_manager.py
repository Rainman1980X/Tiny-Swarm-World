from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PortFileManager(ABC):
    """Central interface for file management."""

    @abstractmethod
    def load(self, path: Path) -> Any:
        """Loads the content of a file.

        Args:
            path (Path): The file path.

        Returns:
            Any: The loaded content.
        """
        pass

    @abstractmethod
    def save(self, path: Path, data: Any) -> None:
        """Saves data to the specified file.

        Args:
            path (Path): The file path.
            data (Any): The data to be saved.
        """
        pass

    @abstractmethod
    def create(self, path: Path, data: Any) -> None:
        """Creates a new file.

        Args:
            path (Path): The file path.
            data (Any): The data to be stored.
        """
        pass

    @abstractmethod
    def delete(self, path: Path) -> bool:
        """Deletes a file.

        Args:
            path (Path): The file path.

        Returns:
            bool: True if the file was deleted, False otherwise.
        """
        pass
