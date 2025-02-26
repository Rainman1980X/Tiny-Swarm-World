import asyncio
from typing import Dict

from domain.command.command_executer.command_executer import CommandExecuter
from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.logging.logger_factory import LoggerFactory
from infrastructure.ui.installation.installation_ui import InstallationUI


class CommandRunnerUI:
    """
    Handles the UI initialization and asynchronous execution of commands.
    """

    def __init__(self, command_list: Dict[str, Dict[int, ExecutableCommandEntity]]):
        """
        Initializes the UI and command execution logic.

        :param command_list: Dictionary mapping instances to their respective command entities.
        """
        self.command_list = command_list
        self.instances = list(command_list.keys())
        self.ui = InstallationUI(self.instances)
        self.command_execute = CommandExecuter(ui=self.ui)
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.logger.info(f"CommandRunnerUI initialized {self.instances} instances")

    async def run(self):
        """
        Runs the UI and executes commands asynchronously.
        """
        # Start the UI in a separate thread
        self.ui.run_in_thread()

        # Execute all commands concurrently as asyncio tasks
        tasks = [
            asyncio.create_task(self.command_execute.execute(self.command_list[vm]))
            for vm in self.instances
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Close the UI thread after the last execution
        await self.ui.ui_thread
        return results