from typing import Dict

from application.ports.port_command_factory import PortCommandRunnerFactory
from application.ports.repositories.port_command_repository import PortCommandRepository
from application.ports.repositories.port_vm_repository import PortVmRepository
from domain.command.command_builder.strategies.manager_strategy import ManagerStrategy
from domain.command.command_builder.strategies.none_strategy import NoneStrategy
from domain.command.command_builder.strategies.worker_strategy import WorkerStrategy
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType


class CommandBuilder:
    executable_commands: [dict[str, dict[int, ExecutableCommandEntity]]]

    def __init__(self,
                 vm_repository: PortVmRepository,
                 command_repository: PortCommandRepository,
                 command_runner_factory: PortCommandRunnerFactory):
        """
        :param vm_repository: list of VMs
        :param command_repository: command repository of multipass init process
        """
        self.vm_repository = vm_repository
        self.command_runner_factory = command_runner_factory
        self.command_repository = command_repository
        self.executable_commands = {}

        self.STRATEGY_MAP = {
            VmType.MANAGER: ManagerStrategy(vm_type=VmType.MANAGER, vm_repository=self.vm_repository,command_runner_factory=self.command_runner_factory),
            VmType.WORKER: WorkerStrategy(vm_type=VmType.WORKER, vm_repository=self.vm_repository,command_runner_factory=self.command_runner_factory),
            VmType.NONE: NoneStrategy(vm_type=VmType.NONE, vm_repository=self.vm_repository,command_runner_factory=self.command_runner_factory),
        }

    def get_command_list(self) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        command_dict = self.command_repository.get_all_commands()

        for key, command in command_dict.items():
            for vm_type in command.vm_type:
                strategy = self.STRATEGY_MAP.get(vm_type.value)
                strategy.categorize(command, self.executable_commands)
        return self.executable_commands
