import os
from typing import Dict

from ruamel.yaml import YAML

from domain.command.command_entity import CommandEntity
from ports.port_command_repository import CommandRepository

class CommandRepositoryYaml(CommandRepository):
    """
    Loads and manages the task list from a YAML file using ruamel.yaml.
    """
    def __init__(self, config_path=None):
        """
        :param config_path: Path to the YAML file
        """
        self.config_path = os.path.abspath(config_path)
        self.yaml = YAML()
        self.data = None

        # Load existing data
        self.__load()

    def __load(self) -> None:

        """Loads the YAML configuration file."""

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"YAML file {self.config_path} does not exist.")

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self.data = self.yaml.load(file) or {}
        except Exception as e:
            raise Exception(f"Error loading YAML file: {str(e)}")

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
