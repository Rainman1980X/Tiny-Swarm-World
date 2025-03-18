from typing import Dict

from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.ui.command_async_runner_ui import AsyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class NetworkService:
    def __init__(self):
        self.ui = None
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):
        self.logger.info("initialisation of network")
        command_list = self._setup_commands_init("command_network_setup_yaml.yaml")
        runner_ui = AsyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"initialisation of multipass : {result}")

    def _setup_commands_init(self, config_file: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = PortCommandRepositoryYaml(filename=config_file)
        self.logger.info(f"getting command list from {config_file}")

        command_builder: CommandBuilder = CommandBuilder(
            command_repository=multipass_command_repository,
            command_runner_factory=CommandRunnerFactory())

        return command_builder.get_command_list()
