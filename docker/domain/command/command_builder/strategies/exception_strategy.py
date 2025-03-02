from typing import Dict

from domain.command.command_builder.strategies.command_builder_strategy import VmTypeStrategy
from domain.command.command_entity import CommandEntity
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from application.ports.repositories.port_vm_repository import PortVmRepository


class InvalidVmTypeStrategy(VmTypeStrategy):
    def __init__(self, vm_type: VmType, vm_repository: PortVmRepository = None, command_runner_factory=None):
        super().__init__(vm_type=vm_type, vm_repository=vm_repository,command_runner_factory=command_runner_factory)

    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]]):
        raise ValueError(f"Invalid vm found: {command.vm_type}")