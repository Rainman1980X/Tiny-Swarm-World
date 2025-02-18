from typing import Dict, List

from ruamel.yaml import YAML

from docker.domain.multipass.command_task_entity import TaskEntity
from docker.ports.port_command_runner import CommandRunner
from docker.ports.port_command_task_repository import CommandTaskRepository

CONFIG_PATH = "config/multipass_command_repository.yaml"


class TaskRepositoryYaml(CommandTaskRepository):
    """
    Lädt und verwaltet die Task-Liste aus einer YAML-Datei mithilfe von ruamel.yaml.
    """

    def __init__(self, async_commandrunner: CommandRunner, multipass_commandrunner: CommandRunner,
                 config_path=CONFIG_PATH):
        """
        :param config_path: Pfad zur YAML-Datei
        :param async_commandrunner: CommandRunner für async-Befehle
        :param multipass_commandrunner: CommandRunner für Multipass-Befehle
        """
        self.config_path = config_path
        self.async_commandrunner = async_commandrunner
        self.multipass_commandrunner = multipass_commandrunner
        self.yaml = YAML()

        # Lade vorhandene Daten
        self.data = self.__load()

    def __load(self) -> Dict:
        """Lädt die YAML-Datei."""
        try:
            with open(self.config_path, "r") as file:
                return self.yaml.load(file) or {}
        except FileNotFoundError:
            print(f"Warning: YAML file '{self.config_path}' not found. Creating new structure.")
            return {}

    def get_all_tasks(self) -> Dict[str, List[TaskEntity]]:
        """
        Gibt alle Tasks aus dem YAML-File zurück.
        """
        task_dict = {}

        for vm_name, vm_data in self.data.items():
            tasks = []
            for task in vm_data.get("tasks", []):
                runner = self.async_commandrunner if task["runner"] == "async" else self.multipass_commandrunner
                tasks.append(
                    TaskEntity(
                        step_index=task["step-index"],
                        description=task["description"],
                        command_runner=runner,
                        command=task["command"]
                    )
                )

            # Sortiere nach step_index
            tasks.sort(key=lambda t: t.step_index)
            task_dict[vm_name] = tasks

        return task_dict
