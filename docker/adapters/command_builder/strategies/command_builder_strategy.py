from abc import ABC, abstractmethod
from typing import Dict

from adapters.command_runner.command_runner_factory import CommandRunnerFactory
from domain.command.command_entity import CommandEntity
from domain.command.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from ports.port_vm_repository import VmRepository


class VmTypeStrategy(ABC):
    """"Abstract strategy class for processing VM types."""
    def __init__(self
                 ,vm_type: VmType
                 ,command_runner_factory: CommandRunnerFactory = CommandRunnerFactory()
                 ,vm_repository: VmRepository = None):

        self.command_runner_factory = command_runner_factory
        self.vm_type = vm_type
        self.vm_repository = vm_repository

    @abstractmethod
    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]]):
        """Inserts the command into the respective group based on its index."""
        pass
