import asyncio

from docker.adapters.exceptions.exception_command_execution import CommandExecutionError
from docker.ports.port_command_runner import CommandRunner


class MultipassCommandRunner(CommandRunner):
    """
    A class to run shell commands inside a specific Multipass VM with thread-safe updates and error handling.
    """

    def __init__(self, instance: str):
        self.instance = instance
        self.status = {
            "current_step": "Initialized",
            "result": None,
        }

        # Use asyncio.Lock for asynchronous operations
        self.lock = asyncio.Lock()

    async def run(self, command: str) -> str:
        full_command = f"multipass exec {self.instance} -- bash -c '{command}'"

        async with self.lock:
            self.status["current_step"] = "Executing command"
            self.status["result"] = "Running..."

        try:
            # Execute the command using asyncio.create_subprocess_shell
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                async with self.lock:
                    self.status["result"] = "Success"
                print(f"Command output for instance '{self.instance}': {stdout.decode().strip()}")
                return stdout.decode().strip()
            else:
                async with self.lock:
                    self.status["result"] = "Error"
                raise CommandExecutionError(
                    command=full_command,
                    return_code=process.returncode,
                    stdout=stdout.decode(),
                    stderr=stderr.decode()
                )

        except Exception as e:
            async with self.lock:
                self.status["result"] = "Error"
            raise CommandExecutionError(
                command=full_command,
                return_code=-1,
                stdout="",
                stderr=str(e),
            ) from e
