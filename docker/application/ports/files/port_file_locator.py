from abc import ABC, abstractmethod


class PortFileLocator(ABC):
    """
    Defines the interface for finding files in different sources (local, cloud, etc.).
    """

    @abstractmethod
    def find_file_path(self) -> str:
        """
        Searches for the specified file and returns its full path.

        Returns:
            str: The full path to the file.

        Raises:
            FileNotFoundError: If the file cannot be found.
        """
        pass
