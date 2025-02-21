from enum import Enum


class CommandRunnerType(str, Enum):
    ASYNC = "async"
    MULTIPASS = "multipass"
    REST = "rest"
    ANSIBLE = "ansible"

    @staticmethod
    def get_enum_from_value(value: str) -> "CommandRunnerType":
        for enum_member in CommandRunnerType:
            if enum_member.value == value:
                return enum_member
        raise ValueError(f"Value '{value}' does not match any CommandRunnerType.")

