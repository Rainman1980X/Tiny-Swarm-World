from docker.domain.command.command_entity import CommandEntity
from docker.ports.port_command_runner import CommandRunner


class Task:

    def __init__(self, command_entity: CommandEntity, command_runner: CommandRunner ):

        self.command_entity = command_entity
        self.command_runner = command_runner
