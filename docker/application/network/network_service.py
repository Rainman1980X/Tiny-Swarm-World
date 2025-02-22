from typing import Dict

from adapters.command_builder.command_builder import CommandBuilder
from adapters.repositories.command_multipass_init_repository_yaml import CommandRepositoryYaml
from domain.command.excecuteable_commands import ExecutableCommandEntity
from domain.network.network import Network
from infrastructure.ui.installation.command_runner_ui import CommandRunnerUI
from ports.port_yaml_manager import YamlManager


class NetworkService:
    def __init__(self, yaml_manager: YamlManager):
        self.port = yaml_manager

    async def run(self, network_data: Network):

        command_list = self.__setup_commands_init("config/command_network_setup_yaml.yaml")
        runner_ui = CommandRunnerUI(command_list)
        await runner_ui.run()

        data = self.port.create(network_data)
        self.port.save()

    def __setup_commands_init(self, config_path: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = CommandRepositoryYaml(config_path=config_path)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository)

        return command_builder.get_command_list()