from abc import ABC, abstractmethod
from typing import Dict

from domain.command.command_entity import CommandEntity


class CommandRepository(ABC):
    """
    Interface for a task repository.
    """

    @abstractmethod
    def get_all_commands(self) -> Dict[int, CommandEntity]:
        """
        Returns all saved tasks.
        """
        pass
