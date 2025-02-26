import asyncio
from sys import stdout

from application.ports.port_command_runner import PortCommandRunner


class RestApiPortCommandRunner(PortCommandRunner):

    def __init__(self):
        super().__init__()
        # Use asyncio.Lock for asynchronous operations
        self.lock = asyncio.Lock()

    async def run(self, command: str) -> str:
        async with self.lock:
            self.status["current_step"] = "Executing command"
            self.status["result"] = "Running..."

        #do something
        async with self.lock:
            self.status["result"] = "Success"

        return stdout.decode('utf-8').strip()