import os
from typing import List, Optional

from ruamel.yaml import YAML

from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder
from docker.domain.multipass.vm_entity import VmEntity
from docker.ports.port_vm_repository import IVMRepository

CONFIG_PATH = "config/vms_repository.yaml"


class VMRepositoryYaml(IVMRepository):
    """YAML-based VM repository using FluentYAMLBuilder."""

    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.yaml_builder = FluentYAMLBuilder("VMRepositories")
        self.yaml = YAML()
        self.loaded_data = None
        self.__load()

    def __load(self) -> None:
        """Loads the YAML configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"YAML file {self.config_path} does not exist.")

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self.loaded_data = self.yaml.load(file) or {}
        except Exception as e:
            raise Exception(f"Error loading YAML file: {str(e)}")

    def save(self) -> None:
        """Saves the YAML configuration file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as file:
                file.write(self.yaml_builder.to_yaml())
        except Exception as e:
            raise Exception(f"Error saving YAML file: {str(e)}")

    def get_all_vms(self) -> List[VmEntity]:
        """Retrieves all VMs as VmEntity objects."""
        return [VmEntity(**vm) for vm in self.loaded_data.get("vms", [])]

    def get_vm_by_name(self, vm_instance: str) -> Optional[VmEntity]:
        """Finds a VM by its name."""
        for vm in self.get_all_vms():
            if vm.vm_instance == vm_instance:
                return vm
        return None

    def add_vm(self, vm: VmEntity) -> None:
        """Adds a new VM to the YAML configuration."""
        self.yaml_builder.add_child("vms", stay=True) \
            .add_child("vm", stay=True) \
            .add_child("id", str(vm.id)) \
            .up() \
            .add_child("vm_instance", vm.vm_instance) \
            .up() \
            .add_child("ipaddress", vm.ipaddress) \
            .up() \
            .add_child("gateway", vm.gateway) \
            .up() \
            .add_child("memory", vm.memory) \
            .up() \
            .add_child("disk", vm.disk) \
            .up()
        self.save()

    def remove_vm(self, name: str) -> None:
        """Deletes a VM by name."""
        all_vms = self.get_all_vms()
        for vm in all_vms:
            if vm.vm_instance == name:
                try:
                    self.yaml_builder.navigate_to(["vms", "vm", "id", str(vm.id)]).delete_current()
                    self.save()
                    return
                except KeyError:
                    raise ValueError(f"VM {name} not found.")
        raise ValueError(f"VM {name} not found.")

    def update_vm(self, vm: VmEntity) -> None:
        """Updates an existing VM."""
        self.remove_vm(vm.vm_instance)
        self.add_vm(vm)

    def find_vm(self, vm_id: str) -> Optional[VmEntity]:
        """Finds a VM by its unique ID."""
        for vm in self.get_all_vms():
            if str(vm.id) == vm_id:
                return vm
        return None

    def find_all_vms(self) -> List[VmEntity]:
        """Retrieves all VMs from the YAML file."""
        return self.get_all_vms()
