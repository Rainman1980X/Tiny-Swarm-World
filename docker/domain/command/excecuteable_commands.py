from pydantic import BaseModel, Field

from ports.port_command_runner import CommandRunner


class ExecutableCommandEntity(BaseModel):
    """
    :param index: order of execution (1, 2, 3, ...)
    :param vm_instance_name: VM instance name
    :param description: Description of the command
    :param command: The actual executable command
    :param runner: CommandRunner type (async, multipass, ...)
    """

    index: int = Field(default=None)
    vm_instance_name: str = Field(default=None)
    description: str = Field(default=None)
    command: str = Field(default=None)
    runner: CommandRunner = Field(default=None)

    # Model configuration to allow arbitrary types
    model_config = {
        "arbitrary_types_allowed": True
    }
