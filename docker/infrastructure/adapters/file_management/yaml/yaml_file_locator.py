import os

from application.ports.file_management.port_file_locator import PortFileLocator
from infrastructure.adapters.file_management.path_normalizer import PathNormalizer


class YamlFileLocator(PortFileLocator):
    """
    Adapter for locating configuration file_management in standard locations.
    """

    def __init__(self, filename: str, additional_paths: list = None):
        self.filename = filename

        self.search_paths = [
            PathNormalizer(os.path.join(os.getcwd(), "config")).normalize(),  # Default config directory
            PathNormalizer(os.getcwd()).normalize()  # Root working directory
        ]

        self.search_paths.insert(1, PathNormalizer(os.path.dirname(os.path.abspath(__file__))).normalize())

        if additional_paths:
            self.search_paths.extend([PathNormalizer(path).normalize() for path in additional_paths])

    def find_file_path(self) -> str:
        """
        Searches for the configuration file in standard config locations.

        Returns:
            str: The full path to the configuration file.

        Raises:
            FileNotFoundError: If the file is not found.
        """
        for directory in self.search_paths:
            normalized_directory = PathNormalizer(directory).normalize()
            file_path = PathNormalizer(os.path.join(normalized_directory, self.filename)).normalize()
            if os.path.isdir(normalized_directory) and os.path.isfile(file_path):
                return file_path

        raise FileNotFoundError(f"Configuration file '{self.filename}' not found in expected paths: {self.search_paths}")
