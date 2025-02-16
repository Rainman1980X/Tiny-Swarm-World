import os
from typing import List

from ruamel.yaml import YAML

from docker.adapters.exceptions.exception_yaml_handling import YAMLHandlingError
from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder
from docker.domain.multipass.vm_entity import VmEntity
from docker.ports.port_vm_repository import IVMRepository

CONFIG_PATH = "config/vms.yaml"


class VMRepositoryYaml(IVMRepository):
    """YAML-based implementation of the VM repository using FluentYAMLBuilder."""

    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.yaml_builder = FluentYAMLBuilder("VMRepositories")
        self.yaml = YAML()
        self.loaded_data = None
        self.__load()

    def __load(self) -> None:
        """Loads an existing VMRepositories configuration file."""

        if not os.path.exists(self.config_path):
            raise YAMLHandlingError(self.config_path,
                                    Exception(f"Failed to load file: {self.config_path} does not exist."))

        if os.path.getsize(self.config_path) == 0:
            raise YAMLHandlingError(self.config_path, Exception(f"Failed to load file: {self.config_path} is empty."))

        if not self.config_path.endswith(('.yaml', '.yml')):
            raise YAMLHandlingError(self.config_path,
                                    Exception(
                                        f"Failed to load file: Unsupported file extension for {self.config_path}."))

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self.loaded_data = self.yaml.load(file) or {}
                self.is_valid = bool(self.loaded_data)  # Valid if data is not empty

                if not self.is_valid:
                    raise YAMLHandlingError(self.config_path, Exception("File contains invalid or empty YAML data"))
        except Exception as e:
            self.is_valid = False
            raise YAMLHandlingError(self.config_path, e)

    def save(self, config_path: str = None) -> None:
        """Saves the generated Netplan configuration file."""
        if not config_path:
            config_path = self.config_path
        try:
            with open(config_path, "w", encoding="utf-8") as file:
                file.write(self.yaml_builder.to_yaml())
            print(f"YAML file saved successfully: {config_path}")
        except Exception as e:
            raise YAMLHandlingError(config_path, e)

    def get_all_vms(self) -> List[VmEntity]:
        """Retrieves all VMs from the configuration."""
        return [VmEntity(**vm) for vm in self.loaded_data.get("vms", [])]

    def get_vm_by_name(self, name: str) -> VmEntity:
        """Finds a VM by its name."""
        for vm in self.get_all_vms():
            if vm.name == name:
                return vm
        raise ValueError(f"VM {name} not found")

    def add_vm(self, vm: VmEntity) -> None:
        """Adds a new VM to the configuration."""
        data = self._load_config()
        if any(existing_vm["name"] == vm.name for existing_vm in data["vms"]):
            raise ValueError(f"VM {vm.name} already exists")
        data["vms"].append(vm.__dict__)
        self._save_config(data)

    def remove_vm(self, name: str) -> None:
        """Removes a VM by its name."""
        data = self._load_config()
        updated_vms = [vm for vm in data.get("vms", []) if vm["name"] != name]
        if len(updated_vms) == len(data["vms"]):
            raise ValueError(f"VM {name} not found")
        data["vms"] = updated_vms
        self._save_config(data)

    def update_vm(self, vm: VmEntity) -> None:
        """Updates an existing VM configuration."""
        data = self._load_config()
        for i, existing_vm in enumerate(data["vms"]):
            if existing_vm["name"] == vm.name:
                data["vms"][i] = vm.__dict__
                self._save_config(data)
                return
        raise ValueError(f"VM {vm.name} not found, cannot update")
