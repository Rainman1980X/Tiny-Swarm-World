from ruamel.yaml import YAMLError
from ruamel.yaml.parser import ParserError


class YAMLHandlingError(Exception):
    """
    Custom exception for errors occurring during the loading of YAML files.
    """

    def __init__(self, file_name: str, error: Exception = None):
        """
        Constructor for the YAMLLoadError class.

        Args:
            file_name (str): The YAML file that caused the error.
            error (Exception): The original exception caught.
        """
        self.file_name = file_name
        self.original_exception = error

        error_mapping = {
            FileNotFoundError: "FileNotFound",
            PermissionError: "PermissionDenied",
            YAMLError: "YAMLSyntaxError",
            OSError: "IOError",
            ParserError: "YAMLParserError",
            ValueError: "ValueError",
            Exception: "Exception",
        }

        self.error_type = next(
            (name for error_type, name in error_mapping.items() if isinstance(self.original_exception, error_type)),
            "UnknownError"
        )

        # Ensure details are meaningful and not empty
        self.details = str(self.original_exception) if str(self.original_exception) else "No additional details"

        super().__init__(
            f"YAMLLoadError: '{file_name}' encountered an error of type '{self.error_type}'. Details: {self.details}")

    def __str__(self):
        """
        Overrides the __str__() method to provide a meaningful string representation.
        """
        return (
            f"YAMLLoadError: Error while loading '{self.file_name}'\n"
            f"Error Type: {self.error_type}\n"
            f"Details: {self.details}"  # Use the precomputed details
        )
