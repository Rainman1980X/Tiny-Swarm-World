from pathlib import Path

from infrastructure.adapters.file_management.file_locator import FileLocator
from infrastructure.adapters.file_management.path_strategies.path_factory import PathFactory
from infrastructure.dependency_injection.infra_core_di_annotations import inject


class FileSaver:
    """
    Handles saving files in a generic way.
    """

    @inject
    def __init__(self, file_path: Path, path_factory: PathFactory):
        """
        Initializes the file saver with the given file path.
        """
        self.path_factory = path_factory
        self.file_locator = FileLocator(file_path.name)
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
