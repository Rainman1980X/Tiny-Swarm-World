from abc import ABC, abstractmethod


class CommandRunnerUi(ABC):

    @abstractmethod
    async def run(self):
        """
        Runs the UI and executes commands asynchronously.
        """
        pass
