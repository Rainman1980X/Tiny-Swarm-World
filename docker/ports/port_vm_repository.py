from abc import ABC, abstractmethod
from typing import List

from docker.domain.multipass.vm_entity import VmEntity


class IVMRepository(ABC):
    """Interface for the VM repository."""

    @abstractmethod
    def get_all_vms(self) -> List[VmEntity]:
        """Retrieves all VM instances."""
        pass

    @abstractmethod
    def get_vm_by_name(self, name: str) -> VmEntity:
        """Retrieves a specific VM by name."""
        pass

    @abstractmethod
    def add_vm(self, vm: VmEntity) -> None:
        """Adds a new VM to the configuration."""
        pass

    @abstractmethod
    def remove_vm(self, name: str) -> None:
        """Removes a VM by name."""
        pass

    @abstractmethod
    def update_vm(self, vm: VmEntity) -> None:
        """Updates an existing VM configuration."""
        pass
