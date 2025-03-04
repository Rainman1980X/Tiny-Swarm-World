from infrastructure.adapters.file_management.file_manager import FileManager
from infrastructure.adapters.file_management.yaml.yaml_file_loader import YamlFileLoader
from infrastructure.adapters.file_management.yaml.yaml_file_locator import YamlFileLocator
from infrastructure.adapters.file_management.yaml.yaml_file_saver import YamlFileSaver


class YamlFileManager(FileManager):
    """
    Specialized FileManager for YAML configuration files.
    """

    def __init__(self, filename: str = "settings.yaml"):
        """
        Initializes the YAML FileManager with default YAML adapters.

        Args:
            filename (str): The name of the YAML file to manage.
        """
        super().__init__(
            filename=filename,
            locator=YamlFileLocator(filename),
            loader=YamlFileLoader(filename),
            saver=YamlFileSaver(filename)
        )