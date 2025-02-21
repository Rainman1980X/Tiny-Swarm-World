import asyncio

from adapters.exceptions.exception_command_execution import CommandExecutionError
from ports.port_command_runner import CommandRunner


class MultipassCommandRunner(CommandRunner):
    """
    A class to run shell commands inside a specific Multipass VM with thread-safe updates and error handling.
    """

    def __init__(self):
        super().__init__()
        # Use asyncio.Lock for asynchronous operations
        self.lock = asyncio.Lock()

    async def run(self, command: str) -> str:

        async with self.lock:
            self.status["current_step"] = "Executing command"
            self.status["result"] = "Running..."

        try:
            # Execute the command using asyncio.create_subprocess_shell
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                async with self.lock:
                    self.status["result"] = "Error"
                raise CommandExecutionError(
                    command=command,
                    return_code=process.returncode,
                    stdout=stdout.decode(),
                    stderr=stderr.decode()
                )

            async with self.lock:
                self.status["result"] = "Success"

            return stdout.decode('utf-8').strip()

        except Exception as e:

            async with self.lock:
                self.status["result"] = "Error"

            raise CommandExecutionError(
                command=command,
                return_code=-1,
                stdout="",
                stderr=str(e),
            ) from e
