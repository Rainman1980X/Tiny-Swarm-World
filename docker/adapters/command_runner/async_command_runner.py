import asyncio

from docker.adapters.exceptions.exception_command_execution import CommandExecutionError
from docker.ports.port_command_runner import CommandRunner


class AsyncCommandRunner(CommandRunner):
    """
    A class for asynchronously running shell commands and handling their outputs and errors.
    """

    async def run(self, command: str, timeout: int = None) -> str:

        try:
            # Start the subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for the process to complete with a timeout
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            # Check for a non-zero return code
            if process.returncode != 0:
                raise CommandExecutionError(
                    command=command,
                    return_code=process.returncode,
                    stdout=stdout.decode('utf-8'),
                    stderr=stderr.decode('utf-8'),
                )

            return stdout.decode('utf-8').strip()

        except asyncio.TimeoutError:
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # Special code for timeouts
                stdout="",
                stderr=f"Command timed out after {timeout} seconds.",
            )

        except Exception as e:
            # Handle unexpected exceptions
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # Special code for unknown errors
                stdout="",
                stderr=f"An unexpected error occurred: {str(e)}",
            ) from e
