from docker.domain.network.network import Network
from docker.ports.port_yaml_manager import YamlManager


class NetworkService:
    def __init__(self, yaml_manager: YamlManager, file_name: str = "cloud-init-manager.yaml"):
        self.port = yaml_manager
        self.file_name = file_name

    def run(self, networkdata: Network):
        data = self.port.create(networkdata)
        self.port.save(data, self.file_name)
