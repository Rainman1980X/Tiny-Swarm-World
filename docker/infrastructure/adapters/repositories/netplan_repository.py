from typing import Any

from ruamel.yaml import YAML

from application.ports.repositories.port_yaml_repository import PortYamlRepository
from domain.network.network import Network
from infrastructure.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from infrastructure.adapters.file_management.yaml.yaml_builder import FluentYAMLBuilder
from infrastructure.adapters.file_management.yaml.yaml_file_manager import YamlFileManager
from infrastructure.logging.logger_factory import LoggerFactory


class PortNetplanRepositoryYaml(PortYamlRepository):
    """
    Manages the creation, validation, and saving of Netplan configuration using YamlFileManager.
    """

    def __init__(self, file_name: str = "cloud-init-manager.yaml"):
        self.file_name = file_name
        self.yaml_manager = YamlFileManager(filename=self.file_name)
        self.builder = FluentYAMLBuilder("network")
        self.yaml = YAML()  # Use ruamel.yaml
        self.yaml.default_flow_style = False  # Ensure correct indentation
        self.yaml.indent(mapping=2, sequence=4, offset=2)  # Better formatting
        self.logger = LoggerFactory.get_logger(self.__class__)

    def create(self, data: Network) -> Any:
        """Creates a Netplan configuration with static IP, routes, and nameservers."""

        self.logger.info(f"Creating Netplan configuration: {data}")
        return (
            self.builder
            .add_child("version", 2, stay=True)  # Netplan version
            .add_child("renderer", "networkd", stay=True)  # Renderer (networkd or NetworkManager)
            .add_child("ethernets")  # Add `ethernets`
            .add_child("ens3")  # Add a specific interface (e.g., ens3)
            .add_child("dhcp4", "no", stay=True)  # Disable DHCP
            .add_child("addresses", [f"{data.ip_address}/24"], stay=True)
            .add_child("routes", [{"to": "0.0.0.0/0", "via": f"{data.gateway}"}],
                       stay=True)  # Define a list for IP addresses
            .add_child("nameservers")
            .add_child("addresses", ["8.8.8.8", "8.8.4.4"], stay=True)
            .build()
        )

    def load(self) -> Any:
        """Loads an existing Netplan configuration file."""
        try:
            return self.yaml_manager.load()
        except FileNotFoundError:
            self.logger.error(f"Netplan configuration file {self.file_name} not found.")
            return {}

    def save(self) -> None:
        """Saves the generated Netplan configuration file."""
        self.logger.info(f"Saving Netplan configuration: {self.builder}")
        try:
            self.yaml_manager.save(self.builder.to_yaml())
            self.logger.info(f"YAML file saved successfully: {self.file_name}")
        except Exception as e:
            self.logger.exception(f"Exception occurred while saving YAML: {str(e)}")
            raise YAMLHandlingError(self.file_name, e)
