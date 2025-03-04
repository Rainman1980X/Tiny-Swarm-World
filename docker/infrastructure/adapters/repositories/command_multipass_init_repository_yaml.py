from typing import Dict

from ruamel.yaml import YAML

from application.ports.repositories.port_command_repository import PortCommandRepository

from domain.command.command_entity import CommandEntity
from infrastructure.adapters.file_management.yaml.yaml_file_manager import YamlFileManager


class PortCommandRepositoryYaml(PortCommandRepository):
    """
    Loads and manages the task list from a YAML file using ruamel.yaml.
    """

    def __init__(self, yaml_file_manager: YamlFileManager = None):
        """
        :param yaml_file_manager: The YAML file manager to use.
        """

        self.yaml_file_manager = yaml_file_manager
        self.yaml = YAML()
        self.data = self.yaml_file_manager.load()

    def get_all_commands(self) -> Dict[int, CommandEntity]:
        """
        Returns all commands from the YAML file.
        """
        task_dict = {}
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
