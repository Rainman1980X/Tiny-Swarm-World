import os
from pathlib import Path
from typing import Any

from application.ports.file_management.port_file_manager import PortFileManager
from infrastructure.adapters.file_management.file_creator import FileCreator
from infrastructure.adapters.file_management.file_loader import FileLoader
from infrastructure.adapters.file_management.file_locator import FileLocator
from infrastructure.adapters.file_management.file_saver import FileSaver
from infrastructure.adapters.file_management.path_normalizer import PathNormalizer
from infrastructure.adapters.file_management.path_strategies.path_factory import PathFactory
from infrastructure.dependency_injection.infra_core_di_annotations import inject


class FileManager(PortFileManager):
    """
    Concrete implementation of the FileManager that manages file loading, saving, creating, and deleting.
    """

    @inject
    def __init__(self,path_factory: PathFactory):
        """
        Initializes the FileManager with locator, loader, saver, and creator instances.
        """

        self.path_factory = path_factory
        # Use lambdas to defer instantiation with required dependencies
        self.locator = lambda filename: FileLocator(
            PathNormalizer(os.path.join(os.getcwd(), "config")).normalize()
        )
        self.loader = FileLoader
        self.saver = FileSaver
        self.creator = FileCreator

    def load(self, path: Path) -> Any:
        """
        Loads the file content using the loader.

        Args:
            path (Path): The file path.

        Returns:
            Any: The loaded data.
        """
        file_loader = self.loader(path)
        return file_loader.load()

    def save(self, path: Path, data: Any) -> None:
        """
        Saves data to the specified file using the saver.

        Args:
            path (Path): The file path.
            data (Any): The data to be saved.
        """
        file_saver = self.saver(path)
        file_saver.save(data)

    def create(self, path: Path, data: Any) -> None:
        """
        Creates a new file using the creator.

        Args:
            path (Path): The file path where the file should be created.
            data (Any): The data to be stored.
        """
        self.creator().create(path, data)


    def delete(self, path: Path) -> bool:
        """
        Deletes a file.

        Args:
            path (Path): The file path.

        Returns:
            bool: True if the file was deleted, False otherwise.
        """
        try:
            file_path = Path(path)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            raise RuntimeError(f"Error deleting file {path}: {e}") from e
