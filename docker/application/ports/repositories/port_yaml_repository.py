from abc import ABC, abstractmethod
from typing import Any


class PortYamlRepository(ABC):
    """
    Abstract base class for YAML repositories.
    """

    @abstractmethod
    def create(self, data) -> Any:
        """
        Creates a new YAML structure from the given data.

        Args:
            data (Any): The data to be converted into a YAML structure.

        Returns:
            Any: The generated YAML structure.
        """
        pass

    @abstractmethod
    def load(self) -> Any:
        """
        Loads and returns the content of the YAML file.

        Returns:
            Any: The parsed YAML data.
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """
        Saves the YAML structure to the file.
        """
        pass
