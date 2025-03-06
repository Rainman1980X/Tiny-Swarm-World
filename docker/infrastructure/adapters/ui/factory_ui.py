import platform

from application.ports.ui.port_ui import PortUI
from infrastructure.adapters.ui.linux_ui import LinuxUI
from infrastructure.adapters.ui.os_types import OsTypes
from infrastructure.adapters.ui.windows_ui import WindowsUi


class FactoryUI:

    def __init__(self):
        self.os_type = OsTypes.get_enum_from_value(platform.system())

    def get_ui(self, **kwargs) -> PortUI:
        if self.os_type == OsTypes.WINDOWS:
            return WindowsUi(**kwargs)
        else :
            return LinuxUI(**kwargs)