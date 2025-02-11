from docker.domain.multipass.vm_entity import VmEntity
from docker.ports.port_command_runner import CommandRunner


class MultipassInitService:
    def __init__(self, multipass_commandrunner=CommandRunner, async_commandrunner=CommandRunner):
        self.multipass_commandrunner = multipass_commandrunner
        self.async_commandrunner = async_commandrunner
        self.swarm_entities = [
            VmEntity(vm_instance="swarm-manager"),
            VmEntity(vm_instance="swarm-worker1"),
            VmEntity(vm_instance="swarm-worker2"),
        ]

    def __create_command_list(self):
        command_list = [
            ("Message", f"multipass launch -n {entity.vm_instance} --memory {entity.memory} --disk {entity.disk}")
            for entity in self.swarm_entities
        ]

        return command_list

    def start_service(self):
        # commandrunner.run()
        pass
