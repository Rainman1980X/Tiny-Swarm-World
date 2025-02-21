from typing import Dict

from adapters.command_builder.strategies.manager_strategy import ManagerStrategy
from adapters.command_builder.strategies.none_strategy import NoneStrategy
from adapters.command_builder.strategies.worker_strategy import WorkerStrategy
from adapters.command_runner.command_runner_factory import CommandRunnerFactory
from domain.command.command_runner_type_enum import CommandRunnerType
from domain.command.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from ports.port_command_repository import CommandRepository
from ports.port_command_runner import CommandRunner
from ports.port_vm_repository import VmRepository


class CommandBuilder:
    executable_commands: [dict[str, dict[int, ExecutableCommandEntity]]]

    def __init__(self,
                 vm_repository: VmRepository,
                 command_repository: CommandRepository ):
        """
        :param vm_repository: list of VMs
        :param command_repository: command repository of multipass init process
        """
        self.vm_repository = vm_repository
        self.command_runner_factory = CommandRunnerFactory()
        self.command_repository = command_repository
        self.executable_commands = {}

        self.STRATEGY_MAP = {
            VmType.MANAGER: ManagerStrategy(vm_type=VmType.MANAGER, vm_repository=self.vm_repository),
            VmType.WORKER: WorkerStrategy(vm_type=VmType.WORKER, vm_repository=self.vm_repository),
            VmType.NONE: NoneStrategy(vm_type=VmType.NONE, vm_repository=self.vm_repository),
        }

    def __replace_command_runner(self, runner: CommandRunnerType) -> CommandRunner:
        return self.command_runner_factory.get_runner(runner)

    def get_command_list(self) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        command_dict = self.command_repository.get_all_commands()

        for key, command in command_dict.items():
            for vm_type in command.vm_type:
                strategy = self.STRATEGY_MAP.get(vm_type.value)
                strategy.categorize(command, self.executable_commands)
        return self.executable_commands
