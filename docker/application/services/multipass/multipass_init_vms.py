from typing import Dict

from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.ui.command_async_runner_ui import AsyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class MultipassInitVms:
    def __init__(self, command_runner_factory=None):
        self.command_runner_factory = command_runner_factory or CommandRunnerFactory()
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):
        self.logger.info("init clean up")
        command_list = self._setup_commands_init("command_multipass_clean_repository_yaml.yaml")
        runner_ui = AsyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"multipass clean up result: {result}")

        self.logger.info("initialisation of multipass")
        command_list = self._setup_commands_init("command_multipass_init_repository_yaml.yaml")
        runner_ui = AsyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"initialisation of multipass: {result}")

    def _setup_commands_init(self, config_file: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        """
        Sets up the initial multipass commands by reading from the YAML configuration.

        Args:
            config_file (str): The path to the YAML configuration file.

        Returns:
            Dict[str, Dict[int, ExecutableCommandEntity]]: The command list.
        """

        multipass_command_repository = PortCommandRepositoryYaml(filename=config_file)

        command_builder: CommandBuilder = CommandBuilder(
            command_repository=multipass_command_repository,
            command_runner_factory=self.command_runner_factory)

        return command_builder.get_command_list()
