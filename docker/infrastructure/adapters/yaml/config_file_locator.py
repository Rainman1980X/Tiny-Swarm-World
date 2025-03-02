import os

from application.ports.files.port_file_locator import PortFileLocator


class ConfigFileLocator(PortFileLocator):
    """
    Adapter for locating configuration files in standard locations.
    """

    def __init__(self, filename: str, additional_paths: list = None):
        self.filename = filename

        self.search_paths = [
            self._normalize_to_linux_path(os.path.join(os.getcwd(), "config")),  # Default config directory
            self._normalize_to_linux_path(os.getcwd())  # Root working directory
        ]

        self.search_paths.insert(1, self._normalize_to_linux_path(os.path.dirname(os.path.abspath(__file__))))

        if additional_paths:
            self.search_paths.extend([self._normalize_to_linux_path(path) for path in additional_paths])

    def find_file_path(self) -> str:
        """
        Searches for the configuration file in standard config locations.

        Returns:
            str: The full path to the configuration file.

        Raises:
            FileNotFoundError: If the file is not found.
        """
        for directory in self.search_paths:
            normalized_directory = self._normalize_to_linux_path(directory)
            file_path = self._normalize_to_linux_path(os.path.join(normalized_directory, self.filename))  # ✅ Fix!

            if os.path.isdir(normalized_directory) and os.path.isfile(file_path):  # ✅ Fix!
                return file_path

        raise FileNotFoundError(f"Configuration file '{self.filename}' not found in expected paths: {self.search_paths}")

