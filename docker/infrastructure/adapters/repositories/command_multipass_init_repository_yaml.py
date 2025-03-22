from pathlib import Path
from typing import Dict

from ruamel.yaml import YAML

from application.ports.repositories.port_command_repository import PortCommandRepository

from domain.command.command_entity import CommandEntity
from infrastructure.adapters.file_management.file_manager import FileManager
from infrastructure.adapters.yaml.yaml_builder import FluentYAMLBuilder
from infrastructure.dependency_injection.infra_core_di_container import infra_core_container
from infrastructure.logging.logger_factory import LoggerFactory


class PortCommandRepositoryYaml(PortCommandRepository):
    """
    Loads and manages the task list from a YAML file using ruamel.yaml.
    """

    def __init__(self,  filename: str ):
        """
        :param filename: The name of the YAML file.
        """
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.file_manager = infra_core_container.resolve(FileManager)
        self.yaml_builder = FluentYAMLBuilder()
        self.yaml = YAML()
        self.data = self.yaml_builder.load_from_string(yaml_content=self.file_manager.load(path=Path(filename))).build()

    def get_all_commands(self) -> Dict[int, CommandEntity]:
        """
        Returns all commands from the YAML file.
        """
        task_dict = {}
        self.logger.info(f"Loading commands from YAML file: {self.data}")
        if not isinstance(self.data.get("commands"), list):
            raise TypeError("Expected 'self.data' to be a list of commands")

        for command in self.data.get("commands"):
            task_dict[command["index"]] = CommandEntity(
                index=command["index"],
                description=command["description"],
                command=command["command"],
                runner=command["runner"],
                command_type=command["command_type"],
                vm_type=command["vm_type"]
            )
        return task_dict
