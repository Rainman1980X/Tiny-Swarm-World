from pathlib import Path
from typing import Any

from infrastructure.adapters.file_management.file_locator import FileLocator


class FileLoader:
    """
    Handles loading of files in a generic way.
    """

    def __init__(self, filename: Path):
        """
        Initializes the file loader with the given filename.
        """
        self.filename = filename
        self.file_locator = FileLocator(filename.name)

    @property
    def path(self) -> Path:
        """Returns the absolute path to the file."""
        return Path(self.file_locator.get_existing_file_path())

    def load(self) -> Any:
        """Loads the file and returns its content."""
        try:
            with open(self.path, 'r', encoding="utf-8") as file:
                return file.read()

        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {self.path}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading file {self.path}: {e}") from e
