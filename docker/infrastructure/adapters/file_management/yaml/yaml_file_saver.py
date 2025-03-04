from application.ports.file_management.port_file_saver import PortFileSaver
from infrastructure.adapters.file_management.yaml.yaml_file_locator import YamlFileLocator


class YamlFileSaver(PortFileSaver):

    def __init__(self, file_path: str):
        self._path = file_path
        self.config_locator = YamlFileLocator(self._path)

    @property
    def path(self) -> str:
        return self.config_locator.find_file_path()

    def save(self,  content: str):
        if self._path :
            with open(self._path, "w", encoding="utf-8") as file:
                file.write(content)


