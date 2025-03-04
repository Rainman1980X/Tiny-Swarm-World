from abc import ABC, abstractmethod
from typing import Any


class PortFileManager(ABC):
    """
    Defines the interface for a FileManager that handles loading, saving, and locating files.
    """

    @abstractmethod
    def get_file_path(self) -> str:
        """
        Finds and returns the full path of the file.

        Returns:
            str: The full absolute path of the file.
        """
        pass

    @abstractmethod
    def load(self) -> Any:
        """
        Loads the file content and returns it.

        Returns:
            Any: The loaded file content.
        """
        pass

    @abstractmethod
    def save(self, data: Any) -> None:
        """
        Saves the given data to the file.

        Args:
            data (Any): The data to be saved.
        """
        pass
