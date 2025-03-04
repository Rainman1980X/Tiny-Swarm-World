import os

from application.ports.file_management.port_file_loader import PortFileLoader
from application.ports.file_management.port_file_locator import PortFileLocator
from application.ports.file_management.port_file_manager import PortFileManager
from application.ports.file_management.port_file_saver import PortFileSaver
from infrastructure.adapters.file_management.path_normalizer import PathNormalizer


class FileManager(PortFileManager):
    """
    Concrete implementation of the FileManager that manages file loading, saving, and locating.
    """

    def __init__(self, filename: str, locator: PortFileLocator, loader: PortFileLoader, saver: PortFileSaver):
        """
        Initializes the FileManager with a locator, loader, and saver.

        Args:
            filename (str): The name of the file to manage.
            locator (PortFileLocator): The locator instance for finding files.
            loader (PortFileLoader): The loader instance for reading files.
            saver (PortFileSaver): The saver instance for writing files.
        """
        self.filename = filename
        self.locator = locator
        self.loader = loader
        self.saver = saver

    def get_file_path(self) -> str:
        """
        Attempts to locate the file and returns its path.

        Returns:
            str: The full path of the file.
        """
        try:
            file_path = self.locator.find_file_path()
        except FileNotFoundError:
            file_path = PathNormalizer(os.path.join(os.getcwd(), "config", self.filename)).normalize()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

        return file_path

    def load(self):
        """
        Loads the file content using the loader.

        Returns:
            Any: The loaded data.
        """
        return self.loader.load()

    def save(self, data):
        """
        Saves data using the saver.

        Args:
            data (Any): The data to be saved.
        """
        self.saver.save(data)
