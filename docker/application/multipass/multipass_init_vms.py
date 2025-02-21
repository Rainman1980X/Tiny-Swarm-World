import threading
from typing import Dict

from adapters.command_builder.command_builder import CommandBuilder
from adapters.command_executer.command_executer import CommandExecuter
from adapters.repositories.command_multipass_init_repository_yaml import CommandRepositoryYaml
from adapters.repositories.vm_repository_yaml import VMRepositoryYaml
from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.ui.installation.installation_ui import InstallationUI

class MultipassInitVms:
    def __init__(self):
        self.ui = None
        self.vm_repository = VMRepositoryYaml()
        self.command_execute = None

    def run(self):

        # init clean up
        command_list = self.__setup_commands_init("config/command_multipass_clean_repository_yaml.yaml")
        self.__run_ui(command_list)

        # initialisation of multipass
        command_list = self.__setup_commands_init("config/command_multipass_init_repository_yaml.yaml")
        self.__run_ui(command_list)

        # first only the commands for the WSL
        # second only the commands for the manager

    def __setup_commands_init(self,config_path : str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = CommandRepositoryYaml(config_path=config_path)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository)

        return command_builder.get_command_list()

    def __run_ui(self,command_list: Dict[str, Dict[int, ExecutableCommandEntity]]):

        instances = []
        for key in command_list:
            instances.append(key)
        self.ui = InstallationUI(instances)
        self.ui.run_in_thread()
        self.command_execute = CommandExecuter(ui=self.ui)

        threads = [threading.Thread(target=self.command_execute.execute, args=(command_list[vm],)) for vm in instances]
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.ui.ui_thread.join()



