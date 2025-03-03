from pathlib import Path

from application.ports.files.port_file_saver import PortFileSaver
from infrastructure.adapters.yaml.config_file_locator import ConfigFileLocator


class YamlConfigSaver(PortFileSaver):

    def __init__(self, file_path: str):
        self._path = file_path
        self.config_locator = ConfigFileLocator(self._path)

    @property
    def path(self) -> str:
        return self.config_locator.find_file_path()

    def save(self,  content: str):
        if self._path :
            with open(self._path, "w") as file:
                file.write(content)


