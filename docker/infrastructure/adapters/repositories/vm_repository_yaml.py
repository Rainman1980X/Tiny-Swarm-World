from pathlib import Path
from typing import List, Optional

from ruamel.yaml import YAML

from infrastructure.adapters.file_management.file_manager import FileManager
from infrastructure.adapters.yaml.yaml_builder import FluentYAMLBuilder
from domain.multipass.vm_entity import VmEntity
from domain.multipass.vm_type import VmType
from application.ports.repositories.port_vm_repository import PortVmRepository
from infrastructure.dependency_injection.infra_core_di_container import infra_core_container

CONFIG_PATH = "vms_repository.yaml"

class PortVmRepositoryYaml(PortVmRepository):
    """YAML-based VM repository using FluentYAMLBuilder."""

    def __init__(self ):
        self.config_path = Path(CONFIG_PATH)
        self.file_manager = infra_core_container.resolve(FileManager)
        self.yaml_builder = FluentYAMLBuilder()
        self.yaml = YAML()
        self.loaded_data = self.yaml_builder.load_from_string(self.file_manager.load(self.config_path)).build()

    def save(self) -> None:
        """Saves the YAML configuration file."""
        try:
            self.file_manager.save(path=self.config_path,data=self.yaml_builder.to_yaml())
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

