import time

from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.logging.logger_factory import LoggerFactory
from infrastructure.ui.installation.installation_ui import InstallationUI

class CommandExecuter:

    executable_commands: [dict[str, dict[int, ExecutableCommandEntity]]]
    def __init__(self,ui:InstallationUI ):
        self.ui = ui
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def execute(self, commands: dict[int, ExecutableCommandEntity]):
        self.logger.info("Command execution started with %d commands.", len(commands))
        current_vm = None
        run_result: dict [int, str] ={}
        for key, executable_command in commands.items():
            current_vm = executable_command.vm_instance_name
            self.logger.info("Executing command on VM '%s' with task: '%s'.", current_vm, executable_command.description)
            try:
                self.logger.info("Before runner '%s'.", current_vm)
                run_result[key] = await executable_command.runner.run(executable_command.command)
                self.logger.info("Command executed successfully on VM '%s'.", current_vm)

            except Exception as e:
                self.logger.error("Failed to execute command on VM '%s'. Error: %s", current_vm, str(e))
                self.ui.update_status(instance=current_vm, task=executable_command.description, step="Error",
                                      result="Failed")
                continue

            self.logger.info("Updating status for VM '%s'.", current_vm)
            runner_status = executable_command.runner.status
            self.ui.update_status(instance=current_vm,
                                  task=executable_command.description,
                                  step=runner_status["current_step"],
                                  result=runner_status["result"])
            self.logger.info("Status updated for VM '%s': step='%s', result='%s'.", current_vm,
                         runner_status["current_step"], runner_status["result"])

            time.sleep(2)

        self.ui.update_status(instance=current_vm, task="closing", step="Finishing", result="Success")
        time.sleep(2)
        self.logger.info("All commands executed. Final status updated.")
        return run_result