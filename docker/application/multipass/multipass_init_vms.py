from typing import Dict

from adapters.command_builder.command_builder import CommandBuilder
from adapters.repositories.command_multipass_init_repository_yaml import CommandRepositoryYaml
from adapters.repositories.vm_repository_yaml import VMRepositoryYaml
from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.ui.installation.command_runner_ui import CommandRunnerUI


class MultipassInitVms:
    def __init__(self):
        self.ui = None
        self.vm_repository = VMRepositoryYaml()
        self.command_execute = None

    async def run(self):
        # init clean up
        command_list = self.__setup_commands_init("config/command_multipass_clean_repository_yaml.yaml")
        runner_ui = CommandRunnerUI(command_list)
        await runner_ui.run()

        # initialisation of multipass
        command_list = self.__setup_commands_init("config/command_multipass_init_repository_yaml.yaml")
        runner_ui = CommandRunnerUI(command_list)
        await runner_ui.run()

        # first only the commands for the WSL
        # second only the commands for the manager

    def __setup_commands_init(self, config_path: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = CommandRepositoryYaml(config_path=config_path)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository)

        return command_builder.get_command_list()
