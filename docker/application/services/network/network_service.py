from typing import Dict

from domain.command.command_builder.command_builder import CommandBuilder
from domain.network.ip_extractor.ip_extractor_builder import IpExtractorBuilder
from domain.network.ip_extractor.strategies.ip_extstractor_types import IpExtractorTypes
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.file_management.yaml.yaml_file_manager import YamlFileManager
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.repositories.netplan_repository import PortNetplanRepositoryYaml
from infrastructure.adapters.repositories.vm_repository_yaml import PortVmRepositoryYaml
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
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
        self.ip_extractor_builder = IpExtractorBuilder()

    async def run(self):
        self.logger.info("initialisation of network")
        command_list = self._setup_commands_init("config/command_network_setup_yaml.yaml")
        runner_ui = CommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"initialisation of multipass : {result}")

        # getting the necessary IPs
        gateway_ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.GATEWAY)
        self.logger.info(f"extracted gateway ip: {gateway_ip}")
        ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.SWAM_MANAGER)
        self.logger.info(f"extracted ip: {ip}")

        vm_instance_names = self.vm_repository.find_vm_instances_by_type(VmType.MANAGER)
        network_data = Network(vm_instance=vm_instance_names[0], ip_address=ip, gateway=gateway_ip)
        self.logger.info("saving network data")

        # Using YamlFileManager to handle configuration storage
        yaml_manager = YamlFileManager(filename="config/netplan.yaml")
        data = PortNetplanRepositoryYaml(yaml_file_manager=yaml_manager)
        data.create(network_data)
        data.save()

    def _setup_commands_init(self, config_file: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        yaml_manager = YamlFileManager(filename=config_file)
        multipass_command_repository = PortCommandRepositoryYaml(yaml_file_manager=yaml_manager)
        self.logger.info(f"getting command list from {config_file}")

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository,
            command_runner_factory=CommandRunnerFactory())

        return command_builder.get_command_list()
