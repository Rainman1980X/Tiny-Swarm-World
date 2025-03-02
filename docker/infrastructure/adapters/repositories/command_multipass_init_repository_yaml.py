from typing import Dict

from ruamel.yaml import YAML

from application.ports.repositories.port_command_repository import PortCommandRepository
from application.ports.files.port_file_loader import PortFileLoader
from domain.command.command_entity import CommandEntity


class PortCommandRepositoryYaml(PortCommandRepository):
    """
    Loads and manages the task list from a YAML file using ruamel.yaml.
    """

    def __init__(self, config_loader: PortFileLoader = None):
        """
        :param config_loader: config loader
        """

        self.config_loader = config_loader
        self.yaml = YAML()
        self.data = None

        # Load existing data
        self.__load()

    def __load(self) -> None:
        """Loads the YAML configuration file."""
        self.data = self.config_loader.load()

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
