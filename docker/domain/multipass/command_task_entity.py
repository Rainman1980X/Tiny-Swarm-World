import uuid

from pydantic import BaseModel, Field

from docker.ports.port_command_runner import CommandRunner


class TaskEntity(BaseModel):
    """
    :param step_index: order of execution (1, 2, 3, ...)
    :param description: Description of the command
    :param command_runner: CommandRunner instance (async or multipass)
    :param command: The actual command
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    step_index: int = Field(default=None)
    description: str = Field(default="")
    command_runner: CommandRunner = Field(default=None)
    command: str = Field(default="")

    # Model configuration to allow arbitrary types
    model_config = {
        "arbitrary_types_allowed": True
    }
