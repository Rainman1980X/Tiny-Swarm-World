from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from application.ports.file_management.port_file_loader import PortFileLoader
from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.file_management.yaml.yaml_file_locator import YamlFileLocator


class YamlFileLoader(PortFileLoader):

    def __init__(self, yaml_filename: str = None):
        """
        Initializes the config loader and automatically searches for the 'config/' subdirectory.
        If such a directory is not found, it falls back to using the current working directory.
        """
        self.yaml = YAML()
        self.yaml_filename = yaml_filename
        self.file_locator = YamlFileLocator(yaml_filename)

    @property
    def path(self) -> str:
        return self.file_locator.find_file_path()

    def load(self):
        """Loads a YAML file and handles errors."""
        try:
            with open(self.path, 'r') as yaml_file:
                data = self.yaml.load(yaml_file)

                # Case 1: File is empty or contains only whitespace
                if data is None or data == "":
                    raise YAMLHandlingError(self.path,
                                            ValueError("The YAML file is empty or contains only whitespace."))

                # Case 2: File contains invalid YAML data but no syntax errors
                if not isinstance(data, (dict, list)):  # YAML should normally be a dictionary or list
                    raise YAMLHandlingError(self.path,
                                            ValueError(
                                                "The YAML file contains invalid data, but it is not a syntax error."))
                return data

        except YAMLHandlingError as e:
            raise e
        except ScannerError as e:
            # Case 3: YAML parsing error (e.g., incorrect indentation, invalid characters)
            raise YAMLHandlingError(self.path, ParserError(f"YAML Syntax Error: {e}")) from e
        except YAMLError as e:
            # Case 4: General YAML error (e.g., unknown YAML constructions)
            raise YAMLHandlingError(self.path, e) from e
        except FileNotFoundError as e:
            # Specific block that already handles FileNotFoundError
            raise YAMLHandlingError(self.path, e) from e
        except Exception as e:
            # Case 5: Unexpected error (e.g., filesystem issues)
            raise YAMLHandlingError(self.path, e) from e

