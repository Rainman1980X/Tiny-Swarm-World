from abc import ABC, abstractmethod
from pathlib import Path


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

    @staticmethod
    def _normalize_to_linux_path(input_path: str) -> str:
        """
        Converts a Windows path into a Linux-compatible path, removing the drive letter if present.

        Args:
            input_path (str): The input file path.

        Returns:
            str: The normalized Linux-style file path.
        """
        # Normalize path and convert to POSIX (Linux-style `/` paths)
        normalized_path = Path(input_path).resolve().as_posix()

        # Remove the drive letter if it exists (e.g., "C:")
        if ":" in normalized_path:
            normalized_path = "/" + "/".join(part for part in normalized_path.split(":")[1:] if part)
            normalized_path = normalized_path.strip("/")

        # Strip trailing and redundant leading slashes
        normalized_path = normalized_path.strip("/")

        # Ensure the path starts with a single leading slash for absolute paths
        return "/" + normalized_path