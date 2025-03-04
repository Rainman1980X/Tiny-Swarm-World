import os
from pathlib import Path

class PathNormalizer:
    """
    Handles path normalization and directory management across different OS.
    """

    def __init__(self, input_path: str):
        self.raw_path = input_path

    def normalize(self) -> str:
        """
        Normalizes the given path to be Linux-compatible, removing Windows drive letters if present.

        Returns:
            str: A normalized absolute file path.
        """
        normalized_path = Path(self.raw_path).resolve().as_posix()

        if ":" in normalized_path:
            normalized_path = "/" + "/".join(part for part in normalized_path.split(":")[1:] if part)
            normalized_path = normalized_path.strip("/")

        normalized_path = normalized_path.strip("/")

        return "/" + normalized_path

    def ensure_directory(self) -> str:
        """
        Ensures that the directory exists and creates it if necessary.

        Returns:
            str: The absolute path to the directory.
        """
        dir_path = Path(self.normalize())

        if not dir_path.exists():
            os.makedirs(dir_path, exist_ok=True)

        return dir_path.as_posix()

    def basename(self) -> str:
        """
        Returns the filename without the full path.

        Returns:
            str: The base name of the file.
        """
        return Path(self.raw_path).name

    def parent_directory(self) -> str:
        """
        Returns the parent directory of the given path.
        Ensures the result is absolute if the input was relative.

        Returns:
            str: The parent directory path.
        """
        parent_path = Path(self.raw_path).parent

        # If the input path was relative, resolve it to absolute
        if not parent_path.is_absolute():
            parent_path = parent_path.resolve()

        return parent_path.as_posix()

