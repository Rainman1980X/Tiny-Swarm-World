import platform

from infrastructure.adapters.file_management.path_strategies.path_linux_strategy import PathLinuxStrategy
from infrastructure.adapters.file_management.path_strategies.path_strategy import PathStrategy
from infrastructure.adapters.file_management.path_strategies.path_windows_strategy import PathWindowsStrategy
from infrastructure.dependency_injection.infra_core_di_annotations import singleton
from infrastructure.os_types import OsTypes

@singleton
class PathFactory:

    def __init__(self):
        self.os_type = OsTypes.get_enum_from_value(platform.system())

    def get_strategy(self) -> PathStrategy:
        """Returns the correct PathStrategy based on OS type."""

        if self.os_type == OsTypes.WINDOWS.value:
            return PathWindowsStrategy()
        else:
            return PathLinuxStrategy()
