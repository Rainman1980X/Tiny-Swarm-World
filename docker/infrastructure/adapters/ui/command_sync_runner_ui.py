import asyncio
from typing import Dict

from domain.command.command_executer.command_executer import CommandExecuter
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from infrastructure.adapters.ui.command_runner_ui import CommandRunnerUi
from infrastructure.logging.logger_factory import LoggerFactory
from infrastructure.adapters.ui.factory_ui import FactoryUI

class SyncCommandRunnerUI(CommandRunnerUi):
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
        self.ui = FactoryUI().get_ui(instances=self.instances, test_mode=False)
        self.command_execute = CommandExecuter(ui=self.ui)
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.logger.info(f"CommandRunnerUI initialized {self.instances} instances")

    async def run(self):
        """
        Runs the UI and executes commands asynchronously.
        """
        # Start the UI in a separate thread
        self.logger.info("start ui")
        self.ui.start_in_thread()

        try:
            # Starte die parallele Ausführung der Befehle für jede VM
            results = []
            for vm in self.instances:
                result = await self.command_execute.execute(self.command_list[vm])
                results.append(result)

            # Fehlerhandling für einzelne VMs
            for vm, result in zip(self.instances, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Execution failed for {vm}: {result}")
                    self.ui.update_status(task="failed", step="execution", result="error", instance=vm)
                else:
                    self.logger.info(f"Execution successful for {vm}")
                    self.ui.update_status(task="completed", step="execution", result="success", instance=vm)

        finally:
            # Aktualisiere die UI mit Abschlussstatus
            self.ui.update_status(task="finished", step="execution", result="success", instance="all")

            # Warte auf das Ende des UI-Threads
            self.logger.info("Waiting for UI thread to close...")
            await self.ui.ui_thread

            self.logger.info("Execution complete.")

        return results