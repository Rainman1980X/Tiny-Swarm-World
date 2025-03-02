from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError

from application.ports.files.port_file_loader import PortFileLoader
from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.yaml.config_file_locator import ConfigFileLocator


class YAMLFileLoader(PortFileLoader):

    def __init__(self, yaml_filename: str = None):
        """
        Initializes the config loader and automatically searches for the 'config/' subdirectory.
        If such a directory is not found, it falls back to using the current working directory.
        """
        self.yaml = YAML()
        self.yaml_filename = yaml_filename
        self.config_locator = ConfigFileLocator(yaml_filename)

    @property
    def yaml_path(self) -> str:
        return self.config_locator.find_file_path()

    def load(self):
        """Loads a YAML file and handles errors."""
        try:
            with open(self.yaml_path, 'r') as yaml_file:
                data = self.yaml.load(yaml_file)

                # Case 1: File is empty or contains only whitespace
                if data is None or data == "":
                    raise YAMLHandlingError(self.yaml_path,
                                            ValueError("The YAML file is empty or contains only whitespace."))

                # Case 2: File contains invalid YAML data but no syntax errors
                if not isinstance(data, (dict, list)):  # YAML should normally be a dictionary or list
                    raise YAMLHandlingError(self.yaml_path,
                                            ValueError(
                                                "The YAML file contains invalid data, but it is not a syntax error."))
                return data

        except YAMLHandlingError as e:
            raise e
        except ScannerError as e:
            # Case 3: YAML parsing error (e.g., incorrect indentation, invalid characters)
            raise YAMLHandlingError(self.yaml_path, ParserError(f"YAML Syntax Error: {e}")) from e

        except YAMLError as e:
            # Case 4: General YAML error (e.g., unknown YAML constructions)
            raise YAMLHandlingError(self.yaml_path, e) from e

        except FileNotFoundError as e:
            # Spezifischer Block, der bereits FileNotFoundError behandelt
            raise YAMLHandlingError(self.yaml_path, e) from e

        except Exception as e:
            # Case 5: Unexpected error (e.g., filesystem issues)
            raise YAMLHandlingError(self.yaml_path, e) from e
