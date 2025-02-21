from enum import Enum


class CommandType(str, Enum):
    HOSTOS = "hostos"
    VM = "vm"
    REST ="rest"