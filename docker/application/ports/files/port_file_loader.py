from abc import ABC, abstractmethod

class PortFileLoader(ABC):

    @property
    @abstractmethod
    def yaml_path(self) -> str:
        """Returns the path to the YAML file."""
        pass

    @abstractmethod
    def load(self) -> dict:
        """Loads the configuration and returns it as a dictionary."""
        pass
