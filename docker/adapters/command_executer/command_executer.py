import time
import logging

from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.ui.installation.installation_ui import InstallationUI

def setup_logger():
    logger = logging.getLogger("CommandExecuter")  # Benannter Logger
    logger.setLevel(logging.INFO)  # Setze die Logebene auf INFO (oder DEBUG für mehr Details)

    # Stelle sicher, dass keine doppelten Handler existieren
    if not logger.handlers:
        # Datei-Handler einrichten
        file_handler = logging.FileHandler("command_executer.log", mode="a")  # Logfile-Name
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")  # Logformat
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Konfiguriere den Logger
logger = setup_logger()

class CommandExecuter:

    executable_commands: [dict[str, dict[int, ExecutableCommandEntity]]]
    def __init__(self,ui:InstallationUI ):
        self.ui = ui

    async def execute(self, commands: dict[int, ExecutableCommandEntity]):
        logger.info("Command execution started with %d commands.", len(commands))
        current_vm = None
        for key, executable_command in commands.items():
            current_vm = executable_command.vm_instance_name
            logger.info("Executing command on VM '%s' with task: '%s'.", current_vm, executable_command.description)
            try:
                logger.info("Before runner '%s'.", current_vm)
                await executable_command.runner.run(executable_command.command)
                logger.info("Command executed successfully on VM '%s'.", current_vm)
            except Exception as e:
                logger.error("Failed to execute command on VM '%s'. Error: %s", current_vm, str(e))
                self.ui.update_status(instance=current_vm, task=executable_command.description, step="Error",
                                      result="Failed")
                continue

                # Status aktualisieren
            runner_status = executable_command.runner.status
            self.ui.update_status(instance=current_vm,
                                  task=executable_command.description,
                                  step=runner_status["current_step"],
                                  result=runner_status["result"])
            logger.info("Status updated for VM '%s': step='%s', result='%s'.", current_vm,
                         runner_status["current_step"], runner_status["result"])

            time.sleep(2)

            # Abschließender Status
        self.ui.update_status(instance=current_vm, task="closing", step="Finishing", result="Success")
        logger.info("All commands executed. Final status updated.")
