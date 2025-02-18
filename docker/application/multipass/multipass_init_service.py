from typing import List

from docker.domain.multipass.command_task_entity import TaskEntity
from docker.ports.port_command_runner import CommandRunner
from docker.ports.port_command_task_repository import CommandTaskRepository
from docker.ports.port_vm_repository import IVMRepository


class MultipassInitService:
    def __init__(self, multipass_commandrunner: CommandRunner = CommandRunner
                 , async_commandrunner: CommandRunner = CommandRunner
                 , vms_repository: IVMRepository = IVMRepository
                 , task_repository: CommandTaskRepository = CommandTaskRepository) -> None:
        """
        :param vms_repository:
        :param task_repository:
        :param async_commandrunner:
        :param multipass_commandrunner:
        :rtype: None
        """
        self.multipass_commandrunner = multipass_commandrunner
        self.async_commandrunner = async_commandrunner
        self.task_repository = task_repository

        if not isinstance(vms_repository, IVMRepository):
            raise TypeError("Repository must be an implementation of IVMRepository.")
        self.repository = vms_repository
        self.swarm_entities = self.repository.get_all_vms()

    def __create_command_list(self) -> List[TaskEntity]:
        command_list = self.task_repository.get_all_tasks()

        return command_list

    def start_service(self):
        # commandrunner.run()
        print("multipass init service started")
        print(self.swarm_entities)
        print(self.__create_command_list())
        pass
