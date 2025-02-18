from abc import ABC, abstractmethod
from typing import List

from docker.domain.multipass.command_task_entity import TaskEntity


class CommandTaskRepository(ABC):
    """
    Interface for a task repository.
    """

    @abstractmethod
    def get_all_tasks(self) -> List[TaskEntity]:
        """
        Returns all saved tasks.
        """
        pass
