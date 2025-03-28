from abc import ABC, abstractmethod
from typing import Dict

from application.ports.commands.port_command_runner_factory import PortCommandRunnerFactory
from domain.command.command_builder.vm_parameter.parameter_type import ParameterType
from domain.command.command_entity import CommandEntity
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType


class CommandBuilderStrategy(ABC):
    """Abstract strategy class for processing VM types."""

    def __init__(self
                 , vm_type: VmType
                 , command_runner_factory: PortCommandRunnerFactory):
        self.command_runner_factory = command_runner_factory
        self.vm_type = vm_type

    @abstractmethod
    def categorize(self, command: CommandEntity, executable_commands: Dict[str, Dict[int, ExecutableCommandEntity]],parameter: Dict[ParameterType,str]=None):
        """Inserts the command into the respective group based on its index."""
        pass
