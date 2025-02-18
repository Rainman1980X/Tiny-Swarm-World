from docker.ports.port_command_runner import CommandRunner
from docker.ports.port_vm_repository import IVMRepository



class MultipassInitService:
    def __init__(self, multipass_commandrunner: CommandRunner = CommandRunner
                 , async_commandrunner: CommandRunner = CommandRunner
                 , repository: IVMRepository = IVMRepository) -> None:
        """
        :param repository:
        :param async_commandrunner:
        :param multipass_commandrunner:
        :rtype: None
        """
        self.multipass_commandrunner = multipass_commandrunner
        self.async_commandrunner = async_commandrunner

        if not isinstance(repository, IVMRepository):
            raise TypeError("Repository must be an implementation of IVMRepository.")
        self.repository = repository
        self.swarm_entities = self.repository.get_all_vms()

    def __create_command_list(self):
        command_list = [
            ("Message", f"multipass launch -n {entity.vm_instance} --memory {entity.memory} --disk {entity.disk}")
            for entity in self.swarm_entities
        ]

        return command_list

    def start_service(self):
        # commandrunner.run()
        print("multipass init service started")
        print(self.swarm_entities)
        pass
