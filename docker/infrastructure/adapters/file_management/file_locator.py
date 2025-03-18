import os
from pathlib import Path

from infrastructure.adapters.file_management.path_normalizer import PathNormalizer


class FileLocator:
    """
    Adapter for locating and ensuring YAML files and directories exist in standard locations.
    """

    def __init__(self, filename: str):
        self.filename = filename

        self.search_paths = [
            PathNormalizer(os.path.join(os.getcwd(), "config")).normalize(),  # Default config directory
            PathNormalizer(os.path.join(os.getcwd(), "config/multipass")).normalize(),
            PathNormalizer(os.path.join(os.getcwd(), "config/docker")).normalize(),
            PathNormalizer(os.path.join(os.getcwd(), "config/network")).normalize(),
            PathNormalizer(os.getcwd()).normalize()  # Root working directory
        ]

        self.search_paths.insert(1, PathNormalizer(os.path.dirname(os.path.abspath(__file__))).normalize())


    def get_existing_file_path(self) -> str:
        """
        Searches for the YAML file in standard config locations **without** creating it.

        Returns:
            str: The full path to the YAML file.

        Raises:
            FileNotFoundError: If the file is not found.
        """
        for directory in self.search_paths:
            file_path = Path(directory) / self.filename

            if file_path.is_file():
                return str(file_path)

        raise FileNotFoundError(f"File '{self.filename}' not found in expected paths: {self.search_paths}")

    def get_existing_directory(self) -> str:
        """
        Searches for an existing directory where the YAML file might be stored.

        Returns:
            str: The first existing directory found.

        Raises:
            FileNotFoundError: If no directory is found.
        """
        for directory in self.search_paths:
            dir_path = Path(directory)

            if dir_path.is_dir():
                return str(dir_path)

        raise FileNotFoundError(f"No valid directories found in: {self.search_paths}")

    def ensure_directory_exists(self) -> str:
        """
        Ensures that the directory for the YAML file exists.

        Returns:
            str: The full path to the directory.
        """
        directory_path = Path(self.search_paths[0])
        directory_path.mkdir(parents=True, exist_ok=True)
        return str(directory_path)

    def ensure_file_exists(self) -> str:
        """
        Ensures that the YAML file and its directory exist.
        If the file does not exist, it creates it.

        Returns:
            str: The full path to the YAML file.
        """
        final_path = Path(self.search_paths[0]) / self.filename
        final_path.parent.mkdir(parents=True, exist_ok=True)

        if not final_path.exists():
            final_path.touch()  # Creates an empty file

        return str(final_path)
