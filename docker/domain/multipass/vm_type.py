from enum import Enum


class VmType(str, Enum):
    MANAGER = "manager"
    WORKER = "worker"
    NONE = "none"

    @staticmethod
    def get_enum_from_value(value: str) -> "VmType":
        for enum_member in VmType:
            if enum_member.value == value:
                return enum_member
        raise ValueError(f"Value '{value}' does not match any CommandRunnerType.")
