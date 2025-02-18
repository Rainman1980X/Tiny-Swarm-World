from docker.domain.network.network import Network
from docker.ports.port_yaml_manager import YamlManager


class NetworkService:
    def __init__(self, yaml_manager: YamlManager):
        self.port = yaml_manager

    def run(self, network_data: Network):
        data = self.port.create(network_data)
        self.port.save()
