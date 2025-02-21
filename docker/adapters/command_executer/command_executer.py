import time

from domain.command.excecuteable_commands import ExecutableCommandEntity
from infrastructure.ui.installation.installation_ui import InstallationUI


class CommandExecuter:

    executable_commands: [dict[str, dict[int, ExecutableCommandEntity]]]
    def __init__(self,ui:InstallationUI ):
        self.ui = ui

    def execute(self, commands: dict[int, ExecutableCommandEntity]):
        current_vm = None
        for key, executable_command in commands.items():
            current_vm = executable_command.vm_instance_name
            executable_command.runner.run(executable_command.command)
            self.ui.update_status(instance=current_vm,
                                  task=executable_command.description,
                                  step=executable_command.runner.status["current_step"],
                                  result=executable_command.runner.status["result"])
            time.sleep(2)
        self.ui.update_status(instance=current_vm, task="closing", step="Finishing", result="Success")