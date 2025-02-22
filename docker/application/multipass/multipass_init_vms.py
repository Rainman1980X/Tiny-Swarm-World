import asyncio
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

    async def run(self):
        # init clean up
        command_list = self.__setup_commands_init("config/command_multipass_clean_repository_yaml.yaml")
        await self.__run_ui(command_list)

        # initialisation of multipass
        command_list = self.__setup_commands_init("config/command_multipass_init_repository_yaml.yaml")
        await self.__run_ui(command_list)

        # first only the commands for the WSL
        # second only the commands for the manager

    def __setup_commands_init(self, config_path: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = CommandRepositoryYaml(config_path=config_path)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository)

        return command_builder.get_command_list()

    async def __run_ui(self, command_list: Dict[str, Dict[int, ExecutableCommandEntity]]):

        instances = list(command_list.keys())

        # Anpassen der UI-Logik für asyncio, falls es möglich ist!
        self.ui = InstallationUI(instances)
        self.ui.run_in_thread()

        # Ein CommandExecuter-Objekt erstellen
        self.command_execute = CommandExecuter(ui=self.ui)

        # Alle Commands parallel als asyncio-Aufgaben ausführen
        tasks = [
            asyncio.create_task(self.command_execute.execute(command_list[vm]))
            for vm in instances
        ]

        # Tasks abwarten
        await asyncio.gather(*tasks)

        # UI-Thread schließen, nach der letzten Ausführung
        await self.ui.ui_thread
