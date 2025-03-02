from typing import List, Optional

from ruamel.yaml import YAML

from infrastructure.adapters.yaml.yaml_builder import FluentYAMLBuilder
from domain.multipass.vm_entity import VmEntity
from domain.multipass.vm_type import VmType
from application.ports.repositories.port_vm_repository import PortVmRepository
from application.ports.files.port_file_loader import PortFileLoader
from infrastructure.adapters.yaml.yaml_config_loader import YAMLFileLoader

CONFIG_PATH = "config/vms_repository.yaml"

class PortVmRepositoryYaml(PortVmRepository):
    """YAML-based VM repository using FluentYAMLBuilder."""

    def __init__(self, config_loader :PortFileLoader = YAMLFileLoader(yaml_filename=CONFIG_PATH)):
        self.config_path = CONFIG_PATH
        self.config_loader = config_loader
        self.yaml_builder = FluentYAMLBuilder("vms")
        self.yaml = YAML()
        self.loaded_data = None
        self.__load()

    def __load(self) -> None:
        """Loads the YAML configuration file."""
        self.loaded_data = self.config_loader.load()

    def save(self) -> None:
        """Saves the YAML configuration file."""
        try:
            with open(self.config_loader.yaml_path, "w", encoding="utf-8") as file:
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
        (self.yaml_builder
         .navigate_to(["vms"])
         .current.add_child(vm.model_dump()))
        self.save()

    def remove_vm(self, name: str) -> None:
        """Deletes a VM by name."""
        all_vms = self.get_all_vms()
        for vm in all_vms:
            if vm.vm_instance == name:
                try:
                    self.yaml_builder.navigate_to(["vms", "vm_instance", str(vm.vm_instance)]).delete_current()
                    self.save()
                    return
                except KeyError:
                    raise ValueError(f"VM {name} not found.")
        raise ValueError(f"VM {name} not found.")

    def update_vm(self, vm: VmEntity) -> None:
        """Updates an existing VM."""
        self.remove_vm(vm.vm_instance)
        self.add_vm(vm)

    def find_all_vms(self) -> List[VmEntity]:
        """Retrieves all VMs from the YAML file."""
        return self.get_all_vms()

    def find_vm_instances_by_type(self, vm_type: VmType) -> List[str]:
        """
        Returns a list of all vm_instance names that belong to specific vm_types.

        Args:
            :param vm_type: the vm_type to filter by.

        Returns:
            :rtype List[str]: List of all VM names that belong to these types.
        """

        # Filter and return matching vm_instance names
        return [
            vm.get("vm_instance")
            for vm in self.loaded_data.get("vms", [])
            if vm.get("vm_type") == vm_type.value and vm.get("vm_instance") is not None
        ]

