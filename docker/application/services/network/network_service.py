from domain.command.command_builder.vm_parameter.command_builder import CommandBuilder
from infrastructure.adapters.repositories.command_multipass_init_repository_yaml import PortCommandRepositoryYaml
from infrastructure.adapters.ui.command_async_runner_ui import AsyncCommandRunnerUI
from infrastructure.logging.logger_factory import LoggerFactory


class NetworkService:
    def __init__(self):
        self.ui = None
        self.command_execute = None
        self.logger = LoggerFactory.get_logger(self.__class__)

    async def run(self):
        self.logger.info("initialisation of network")

        multipass_command_repository = PortCommandRepositoryYaml(filename="command_network_setup_yaml.yaml")
        command_builder: CommandBuilder = CommandBuilder(command_repository=multipass_command_repository)
        command_list = command_builder.get_command_list()

        runner_ui = AsyncCommandRunnerUI(command_list)
        result = await runner_ui.run()
        self.logger.info(f"initialisation of multipass : {result}")
