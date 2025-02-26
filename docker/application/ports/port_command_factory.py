from abc import ABC, abstractmethod
from domain.command.command_runner_type_enum import CommandRunnerType
from application.ports.port_command_runner import PortCommandRunner

class PortCommandRunnerFactory(ABC):
    @abstractmethod
    def get_runner(self, runner_type: CommandRunnerType) -> PortCommandRunner:
        pass
