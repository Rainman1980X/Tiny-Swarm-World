from typing import Dict, Optional

from domain.command.command_builder.vm_parameter.parameter_type import ParameterType
from domain.command.command_builder.vm_parameter.strategies.command_builder_strategy import CommandBuilderStrategy
from domain.command.command_builder.vm_parameter.strategies.command_parameter_builder import CommandParameterBuilder
from domain.command.command_entity import CommandEntity
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.command.command_runner_type_enum import CommandRunnerType
from domain.multipass.vm_type import VmType
from infrastructure.adapters.repositories.vm_repository_yaml import PortVmRepositoryYaml
from infrastructure.logging.logger_factory import LoggerFactory


class ManagerStrategy(CommandBuilderStrategy):

    def __init__(self, vm_type: VmType, command_runner_factory=None):
        super().__init__(vm_type=vm_type, command_runner_factory=command_runner_factory)
        self.vm_repository = PortVmRepositoryYaml()
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.logger.info("ManagerStrategy initialized")
        self.command_parameter_builder= CommandParameterBuilder()

    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]],parameter: Dict[ParameterType,str]=None):
        vm_instance_names = self.vm_repository.find_vm_instances_by_type(self.vm_type)

        if len(vm_instance_names) == 1:
            self.logger.info(f"Found vm instance: {vm_instance_names[0]}")
            vm_instance_name = vm_instance_names[0]
            parameter[ParameterType.VM_INSTANCE] = vm_instance_name
            executable_commands.setdefault(vm_instance_name, {})
            executable_commands[vm_instance_name][command.index] = ExecutableCommandEntity(
                vm_instance_name=vm_instance_name,
                description=command.description.format(vm_instance=vm_instance_name),
                command=self.command_parameter_builder.substitute_command(command.command,parameter),
                runner=self.command_runner_factory.get_runner(CommandRunnerType.get_enum_from_value(command.runner))
            )
