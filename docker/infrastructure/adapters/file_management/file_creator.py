from pathlib import Path
from typing import Any

from infrastructure.adapters.file_management.path_normalizer import PathNormalizer
from infrastructure.adapters.file_management.path_strategies.path_factory import PathFactory
from infrastructure.dependency_injection.infra_core_di_annotations import inject


class FileCreator:
    """Handles the creation of new YAML files."""

    @inject
    def __init__(self, file_path: Path , path_factory: PathFactory):
        """Initializes the YAML file creator."""
        self.path_factory = path_factory
        self._path = Path(file_path) if file_path else None
        self.path_normalizer = PathNormalizer(self._path)

    @property
    def path(self) -> Path:
        """Returns the path of the YAML file."""
        return self._path

    @property
    def name(self) -> str:
        """Returns the name of the file."""
        return self._path.name if self._path else ""

    @path.setter
    def path(self, path: Path) -> None:
        """Sets the file path."""
        self._path = path
        self.path_normalizer = PathNormalizer(self._path,self.path_factory)

    def create(self, path: Path, data: Any) -> Path:
        """Creates a YAML file at the specified path.

        Args:
            path (Path): The file path where the file should be created.
            data (Any): The data to be saved.

        Returns:
            Path: The path of the created file.
        """
        self._path = path
        self.path_normalizer = PathNormalizer(self._path,self.path_factory)

        # Normalize and ensure directory exists
        normalized_path = self.path_normalizer.ensure_directory()
        final_file_path = Path(normalized_path) / self._path.name

        # Write data to file
        with open(final_file_path, "w", encoding="utf-8") as f:
            f.write(str(data))

        return final_file_path
