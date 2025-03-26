from typing import Dict

from domain.command.command_builder.vm_parameter.strategies.command_builder_strategy import CommandBuilderStrategy
from domain.command.command_entity import CommandEntity
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType


class InvalidCommandBuilderStrategy(CommandBuilderStrategy):
    def __init__(self, vm_type: VmType, command_runner_factory=None):
        super().__init__(vm_type=vm_type, command_runner_factory=command_runner_factory)

    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]], parameter: Dict[str, str] = None):
        raise ValueError(f"Invalid vm found: {command.vm_type}")
