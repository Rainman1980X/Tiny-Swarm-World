from abc import ABC, abstractmethod
from typing import Dict

from application.ports.commands.port_command_factory import PortCommandRunnerFactory
from application.ports.repositories.port_vm_repository import PortVmRepository
from domain.command.command_entity import CommandEntity
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType


class VmTypeStrategy(ABC):
    """Abstract strategy class for processing VM types."""

    def __init__(self
                 , vm_type: VmType
                 , command_runner_factory: PortCommandRunnerFactory
                 , vm_repository: PortVmRepository = None):

        self.command_runner_factory = command_runner_factory
        self.vm_type = vm_type
        self.vm_repository = vm_repository

    @abstractmethod
    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]]):
        """Inserts the command into the respective group based on its index."""
        pass
