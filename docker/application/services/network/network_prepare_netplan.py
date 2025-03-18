from typing import Dict

from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from domain.command.command_executer.excecuteable_commands import ExecutableCommandEntity
from domain.multipass.vm_type import VmType
from domain.network.ip_extractor.ip_extractor_builder import IpExtractorBuilder
from domain.network.ip_extractor.strategies.ip_extstractor_types import IpExtractorTypes
from domain.network.network import Network
from infrastructure.adapters.command_runner.command_runner_factory import CommandRunnerFactory
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.repositories.netplan_repository import PortNetplanRepositoryYaml
from infrastructure.adapters.ui.command_async_runner_ui import AsyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class NetworkPrepareNetplan:
    def __init__(self, vm_repository=None, command_runner_factory=None):
        self.command_runner_factory = command_runner_factory or CommandRunnerFactory()
        self.ui = None
        self.command_execute = None
        self.ip_extractor_builder = IpExtractorBuilder()
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):
        self.logger.info("Setup cloud-init-manager.yaml")
        command_list = self._setup_commands_init("command_network_ip_yaml.yaml")
        runner_ui = AsyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"multipass clean up result: {result}")

        # getting the necessary IPs
        gateway_ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.GATEWAY)
        self.logger.info(f"extracted gateway ip: {gateway_ip}")
        ip = self.ip_extractor_builder.build(result=result, ip_extractor_types=IpExtractorTypes.SWAM_MANAGER)
        self.logger.info(f"extracted ip: {ip}")

        vm_instance_names = self.vm_repository.find_vm_instances_by_type(VmType.MANAGER)
        network_data = Network(vm_instance=vm_instance_names[0], ip_address=ip, gateway=gateway_ip)
        self.logger.info("creating network data")

        data = PortNetplanRepositoryYaml()
        data.create(network_data)
        self.logger.info("saving network data")
        data.save()

    def _setup_commands_init(self, config_file: str) -> Dict[str, Dict[int, ExecutableCommandEntity]]:
        """
        Sets up the initial multipass commands by reading from the YAML configuration.

        Args:
            config_file (str): The path to the YAML configuration file.

        Returns:
            Dict[str, Dict[int, ExecutableCommandEntity]]: The command list.
        """

        multipass_command_repository = PortCommandRepositoryYaml(filename=config_file)

        command_builder: CommandBuilder = CommandBuilder(
            vm_repository=self.vm_repository,
            command_repository=multipass_command_repository,
            command_runner_factory=self.command_runner_factory)

        return command_builder.get_command_list()
