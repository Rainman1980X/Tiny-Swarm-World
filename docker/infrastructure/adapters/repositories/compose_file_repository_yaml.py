from application.ports.repositories.port_compose_file_repository import PortComposeFileRepository
from infrastructure.adapters.yaml.yaml_builder import FluentYAMLBuilder


class ComposeFileRepositoryYaml(PortComposeFileRepository):

    def __init__(self):
        pass

    def get_compose_of(self) -> FluentYAMLBuilder:
        pass