from typing import Dict

from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.network.ip_extractor.ip_extractor_builder import IpExtractorBuilder
from domain.network.ip_extractor.strategies.ip_extstractor_types import IpExtractorTypes
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.ui.command_sync_runner_ui import SyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class MultipassDockerSwarmInit:
    def __init__(self, command_runner_factory=None):
        self.command_runner_factory = command_runner_factory or CommandRunnerFactory()
        self.ip_extractor_builder = IpExtractorBuilder()
        self.ui = None
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):
        self.logger.info("Initializing Docker Swarm on Manager")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_setup.yaml")
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"Initializing Docker Swarm on Manager: {result}")

        self.logger.info("Getting Manager IP")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_ip.yaml")
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.SWAM_MANAGER)
        self.logger.info(f"Getting Manager IP: {ip}")

        self.logger.info("Joining Worker Nodes to Swarm")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_ip.yaml")
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.SWAM_MANAGER)
        self.logger.info(f"Getting Manager IP: {ip}")

    def _setup_commands_init(self, config_file: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        """
        Sets up the initial multipass commands by reading from the YAML configuration.

        Args:
            config_file (str): The path to the YAML configuration file.

        Returns:
            Dict[str, Dict[int, ExecutableCommandEntity]]: The command list.
        """

        multipass_command_repository = PortCommandRepositoryYaml(filename=config_file)
        self.logger.info(f"getting command list from {config_file}")
        command_builder: CommandBuilder = CommandBuilder(
            command_repository=multipass_command_repository,
            command_runner_factory=self.command_runner_factory)
        self.logger.info(f"command builder: {command_builder.get_command_list()}")
        return command_builder.get_command_list()
