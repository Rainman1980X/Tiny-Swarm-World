from typing import Dict, Optional

from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from domain.command.command_builder.vm_parameter.parameter_type import ParameterType
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.ui.command_sync_runner_ui import SyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class MultipassDockerSwarmInit:
    def __init__(self):
        self.command_runner_factory = CommandRunnerFactory()
        self.ui = None
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.parameter: Dict[ParameterType, str] = {}

    async def run(self):

        self.logger.info("Initializing Docker Swarm on Manager")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_init.yaml", None)
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"Initializing Docker Swarm on Manager: {result}")

        self.logger.info("Getting join-token for the worker")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_join_token.yaml",None)
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"Getting join-token for the worker: {result}")

        self.logger.info("Getting Manager IP")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_ip.yaml", None)
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        ipaddress = list(result[0].values())[0].split()[0]
        self.parameter[ParameterType.SWARM_MANAGER_IP] = ipaddress
        self.parameter[ParameterType.SWARM_MANAGER_PORT] = "2377"
        self.logger.info(f"Getting Manager IP: {result}")

        self.logger.info("Getting join token")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_manager_join_token.yaml",None)
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        token = result[0][1]
        self.parameter[ParameterType.SWARM_TOKEN] = token
        self.logger.info(f"Getting join token: {token}")

        self.logger.info("Join worker to Swarm")
        command_list = self._setup_commands_init("command_multipass_docker_swarm_join_worker.yaml", self.parameter)
        runner_ui = SyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"Join worker to Swarm: {result}")

    def _setup_commands_init(self, config_file: str, parameter: Optional[Dict[ParameterType, str]]) -> Dict[
        str, Dict[int, ExecutableCommandEntity]]:
        """
        Sets up the initial multipass commands by reading from the YAML configuration.

        Args:
            config_file (str): The path to the YAML configuration file.

        Returns:
            Dict[str, Dict[int, ExecutableCommandEntity]]: The command list.
        """
        parameter = parameter or {}
        multipass_command_repository = PortCommandRepositoryYaml(filename=config_file)
        self.logger.info(f"getting command list from {config_file}")
        command_builder: CommandBuilder = CommandBuilder(
            command_repository=multipass_command_repository, parameter=parameter)
        self.logger.info(f"command builder: {command_builder.get_command_list()}")
        return command_builder.get_command_list()
