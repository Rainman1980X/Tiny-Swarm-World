from typing import Dict

from domain.command.command_builder.command_builder import CommandBuilder
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.repositories.vm_repository_yaml import PortVmRepositoryYaml
from infrastructure.adapters.yaml.netplan_configurator import NetplanConfigurationManagerPortYamlManager
from domain.command.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from domain.network.network import Network
from infrastructure.logging.logger_factory import LoggerFactory
from infrastructure.ui.installation.command_runner_ui import CommandRunnerUI


class NetworkService:
    def __init__(self):
        self.ui = None
        self.vm_repository = PortVmRepositoryYaml()
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):

        self.logger.info("initialisation of network")
        command_list = self.__setup_commands_init("config/command_network_setup_yaml.yaml")
        runner_ui = CommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"initialisation of multipass : {result}")

        vm_instance_names = self.vm_repository.find_vm_instances_by_type(VmType.MANAGER)

        gateway_ip = self.__extract_gateway_ip(result)
        self.logger.info(f"extracted gateway ip: {gateway_ip}")
        ip = self.__extract_ip(result)
        self.logger.info(f"extracted ip: {ip}")

        network_data = Network(vm_instance=vm_instance_names[0],ip_address=ip, gateway=gateway_ip)
        self.logger.info("saving network data")
        data = NetplanConfigurationManagerPortYamlManager()
        data.create(network_data)
        data.save()

    def __setup_commands_init(self, config_path: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        multipass_command_repository = PortCommandRepositoryYaml(config_path=config_path)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository)

        return command_builder.get_command_list()


    def __extract_gateway_ip(self,result):
        self.logger.info(f"extract gateway ip: {result[1]}")
        value2 = result[1][2].strip().split()
        return value2[2] if len(value2) > 2 else None


    def __extract_ip(self,result):
        self.logger.info(f"extract ip: {result[1]}")
        return result[1][3].strip().split()[0]
