from docker.domain.multipass.vm_entity import VmEntity
from docker.ports.port_command_runner import CommandRunner


class MultipassInitService:
    def __init__(self):
        self.commandrunner = CommandRunner()
        self.swarmmanager = VmEntity(vm_instance="swarm-manager")
        self.swarmworker1 = VmEntity(vm_instance="swarm-worker1")
        self.swarmworker2 = VmEntity(vm_instance="swarm-worker2")

    @staticmethod
    def create_command_list():
        return []
