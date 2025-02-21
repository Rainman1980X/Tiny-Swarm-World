from typing import List

from pydantic import BaseModel, Field

from domain.command.command_type_enum import CommandType
from domain.multipass.vm_type import VmType


class CommandEntity(BaseModel):
    """
    :param index: order of execution (1, 2, 3, ...)
    :param description: Description of the command
    :param command: The actual command template
    :param runner: CommandRunner type (async, multipass, ...)
    :param command_type: Command type (HOSTOS, VM, ...)
    :param vm_type: VM types (worker, manager, ...)
    """
    index: int = Field(default=None)
    description: str = Field(default="")
    command: str = Field(default="")
    runner: str = Field(default=None)
    command_type: CommandType = Field(default=CommandType.HOSTOS)
    vm_type: List[VmType] = Field(default_factory=lambda: [VmType.NONE])

    # Model configuration to allow arbitrary types
    model_config = {
        "arbitrary_types_allowed": True
    }
