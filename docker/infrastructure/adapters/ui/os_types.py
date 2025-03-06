
from enum import Enum

class OsTypes(str,Enum):
    WINDOWS = "windows"
    LINUX = "linux"

    @staticmethod
    def get_enum_from_value(value: str) -> "OsTypes":
        for enum_member in OsTypes:
            if enum_member.value.lower() == value.lower():
                return enum_member
        raise ValueError(f"Value '{value}' does not match any OsType.")
