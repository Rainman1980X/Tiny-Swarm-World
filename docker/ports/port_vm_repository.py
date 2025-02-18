from abc import ABC, abstractmethod
from typing import List, Optional

from docker.domain.multipass.vm_entity import VmEntity


class IVMRepository(ABC):
    """Interface for managing VM entities."""

    @abstractmethod
    def get_all_vms(self) -> List[VmEntity]:
        """Retrieves all VM instances.
        :rtype: List[VmEntity]
        """
        pass

    @abstractmethod
    def get_vm_by_name(self, name: str) -> Optional[VmEntity]:
        """Finds a VM by its name."""
        pass

    @abstractmethod
    def add_vm(self, vm: VmEntity) -> None:
        """Adds a new VM to the repository."""
        pass

    @abstractmethod
    def remove_vm(self, name: str) -> None:
        """Removes a VM by name."""
        pass

    @abstractmethod
    def update_vm(self, vm: VmEntity) -> None:
        """Updates an existing VM configuration."""
        pass

    @abstractmethod
    def find_vm(self, vm_id: str) -> Optional[VmEntity]:
        """Finds a VM by its unique ID."""
        pass

    @abstractmethod
    def find_all_vms(self) -> List[VmEntity]:
        """Retrieves all VMs as objects."""
        pass
