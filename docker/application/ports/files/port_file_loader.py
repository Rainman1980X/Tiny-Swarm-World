from abc import ABC, abstractmethod

class PortFileLoader(ABC):

    @property
    @abstractmethod
    def path(self) -> str:
        """Returns the path to the file."""
        pass

    @abstractmethod
    def load(self) -> dict:
        """Loads the configuration and returns it as a dictionary."""
        pass
