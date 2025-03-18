import asyncio

from infrastructure.adapters.exceptions.exception_command_execution import CommandExecutionError
from infrastructure.logging.logger_factory import LoggerFactory
from application.ports.commands.port_command_runner import PortCommandRunner


class AsyncPortCommandRunner(PortCommandRunner):
    """
    A class for asynchronously running shell commands and handling their outputs and errors.
    """

    def __init__(self):
        super().__init__()
        # Use asyncio.Lock for asynchronous operations
        self.lock = asyncio.Lock()
        # Initialize status as a dictionary (if not already handled in the base class)
        self.status = {"current_step": "Not started", "result": "Pending"}  # Default status
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.logger.info("AsyncCommandRunner initialized")

    async def run(self, command: str, timeout: int = 120) -> str:
        self.logger.info(f"Starting subprocess: {command}")
        process = None
        try:
            # Update status
            async with self.lock:
                self.status["current_step"] = "Executing command"
                self.status["result"] = "Running..."

            # Start subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.logger.info(f"Finishing subprocess: {command}")
            # Wait for subprocess to complete
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            # Log output
            self.logger.info(f"Command output: {stdout.decode('utf-8').strip()}")

            # Check process return code
            if process.returncode != 0:
                error_message = stderr.decode('utf-8').strip()  # Read error from stderr
                self.logger.error(f"Command failed with return code {process.returncode}: {error_message}")
                async with self.lock:
                    self.status["result"] = "Error"
                raise CommandExecutionError(
                    command=command,
                    return_code=process.returncode,
                    stdout=stdout.decode('utf-8').strip(),
                    stderr=error_message
                )

            # Update status as successful
            async with self.lock:
                self.status["result"] = "Success"
            self.logger.info(f"Command completed successfully: {command}")

            return stdout.decode('utf-8').strip()

        except asyncio.TimeoutError:
            # Log timeout error
            async with self.lock:
                self.status["result"] = "Error"
            self.logger.error(f"Command timed out after {timeout} seconds: {command}")
            process.kill()
            await process.communicate()
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # -1 = Special return code for timeout
                stdout="",
                stderr=f"Command timed out after {timeout} seconds."
            )

        except Exception as e:
            # Log unexpected errors
            self.logger.exception(f"An unexpected error occurred while executing the command: {command}")
            async with self.lock:
                self.status["result"] = "Error"
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # -1 = Special return code for unexpected errors
                stdout="",
                stderr=f"An unexpected error occurred: {str(e)}"
            ) from e