from typing import Dict

from adapters.command_builder.strategies.command_builder_strategy import VmTypeStrategy
from domain.command.command_entity import CommandEntity
from domain.command.command_runner_type_enum import CommandRunnerType
from domain.command.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from ports.port_vm_repository import VmRepository


class NoneStrategy(VmTypeStrategy):

    def __init__(self, vm_type: VmType, vm_repository: VmRepository = None):
        super().__init__(vm_type=vm_type, vm_repository=vm_repository)

    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]]):
        vm_instance_name = command.command_type.value
        executable_commands.setdefault(vm_instance_name, {})
        executable_commands[vm_instance_name][command.index] =  ExecutableCommandEntity(
        vm_instance_name = vm_instance_name,
        description=command.description.format(vm_instance=vm_instance_name),
        command=command.command.format(vm_instance=vm_instance_name),
        runner=self.command_runner_factory.get_runner(CommandRunnerType.get_enum_from_value(command.runner)))
