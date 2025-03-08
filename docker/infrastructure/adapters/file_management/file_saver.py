from pathlib import Path

from infrastructure.adapters.file_management.file_locator import FileLocator


class FileSaver:
    """
    Handles saving files in a generic way.
    """

    def __init__(self, file_path: Path):
        """
        Initializes the file saver with the given file path.
        """
        self.file_locator = FileLocator(file_path)
        self._path = Path(self.file_locator.ensure_file_exists())

    @property
    def path(self) -> Path:
        """Returns the absolute path to the file."""
        return self._path

    def save(self, content: str):
        """Saves the given content to the file."""
        try:
            with open(self.path, "w", encoding="utf-8") as file:
                file.write(content)

        except Exception as e:
            raise RuntimeError(f"Error saving file {self.path}: {e}") from e
