import os
from typing import Any

from ruamel.yaml import YAML

from docker.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder
from docker.domain.network.network import Network
from docker.ports.port_yaml_manager import YamlManager


class NetplanConfigurationManager(YamlManager):
    """
    Manages the creation, validation, and saving of Netplan configuration files.
    """

    def __init__(self, file_name: str = "cloud-init-manager.yaml"):
        self.file_name = file_name
        self.address = None
        self.gateway = None
        self.loaded_data = None
        self.is_valid = False
        self.builder = FluentYAMLBuilder()
        self.yaml = YAML()  # Use ruamel.yaml
        self.yaml.default_flow_style = False  # Ensure correct indentation
        self.yaml.indent(mapping=2, sequence=4, offset=2)  # Better formatting

    def create(self, data: Network) -> Any:
        """Creates a Netplan configuration with static IP, routes, and nameservers."""

        print(f"Creating Netplan configuration")
        return (
            self.builder
            .add_key("network")  # Top-level "network" key
            .add_entry("version", 2)  # Netplan version
            .add_entry("renderer", "networkd")  # Renderer (networkd or NetworkManager)
            .add_key("ethernets")  # Add `ethernets`
            .add_key("ens3")  # Add a specific interface (e.g., ens3)
            .add_entry("dhcp4", "no")  # Disable DHCP
            .add_list("addresses")  # Define a list for IP addresses
            .add_list_item(f"{data.ip_address}/24")  # Add static IP with subnet mask
            .up()  # Move up to "ens3"
            .add_list("routes")  # Erstellt die `routes`-Liste
            .add_list_item({"to": "0.0.0.0/0", "via": data.gateway})
            .up()
            .add_key("nameservers")  # Add nameservers section
            .add_list("addresses")  # Create a nameservers list
            .add_list_item("8.8.8.8")  # Add Google DNS
            .add_list_item("8.8.4.4")  # Add secondary Google DNS
            .up().up().up()  # Move back up to the root
            .build()
        )

    def load(self, file_path: str = None) -> None:
        """Loads an existing Netplan configuration file."""
        file_path = file_path or self.file_name

        if not os.path.exists(file_path):
            raise YAMLHandlingError(file_path, Exception(f"Failed to load file: {file_path} does not exist."))

        if os.path.getsize(file_path) == 0:
            raise YAMLHandlingError(file_path, Exception(f"Failed to load file: {file_path} is empty."))

        if not file_path.endswith(('.yaml', '.yml')):
            raise YAMLHandlingError(file_path,
                                    Exception(f"Failed to load file: Unsupported file extension for {file_path}."))

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.loaded_data = self.yaml.load(file) or {}
                self.is_valid = bool(self.loaded_data)  # Valid if data is not empty

                if not self.is_valid:
                    raise YAMLHandlingError(file_path, Exception("File contains invalid or empty YAML data"))
        except Exception as e:
            self.is_valid = False
            raise YAMLHandlingError(file_path, e)


    def save(self, data: Any, file_path: str = None) -> None:
        """Saves the generated Netplan configuration file."""
        if not file_path:
            file_path = self.file_name
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                self.yaml.dump(data, file)
            print(f"YAML file saved successfully: {file_path}")
        except Exception as e:
            raise YAMLHandlingError(file_path, e)

    def validate(self, file_path: str = None) -> bool:
        """Validates the syntax of a Netplan YAML file."""
        if not file_path:
            file_path = self.file_name

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.yaml.load(file)  # Try loading the YAML file
            return True
        except Exception as e:  # Fängt alle Fehler ab
            raise YAMLHandlingError(file_path, e)
