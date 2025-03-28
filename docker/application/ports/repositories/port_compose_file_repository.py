
from abc import ABC, abstractmethod
from infrastructure.adapters.yaml.yaml_builder import FluentYAMLBuilder


class PortComposeFileRepository(ABC):

    @abstractmethod
    def get_compose_of(self) -> FluentYAMLBuilder:
        """ Returns the compose file."""
        pass