import subprocess
from threading import Lock

from docker.adapters.exceptions.exception_command_execution import CommandExecutionError  # Exception-Import
from docker.ports.port_command_runner import CommandRunner  # Import der CommandRunner-Basisklasse


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

        self.lock = Lock()

    def run(self, command: str) -> str:
        full_command = f"multipass exec {self.instance} -- bash -c '{command}'"

        with self.lock:
            self.status["current_step"] = "Executing command"
            self.status["result"] = "Running..."

        try:
            # Execute the command with subprocess
            result = subprocess.run(
                full_command,
                shell=True,
                check=True,
                text=True,
                capture_output=True,
            )

            with self.lock:
                self.status["result"] = "Success"

            print(f"Command output for instance '{self.instance}': {result.stdout.strip()}")

            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            # Update the status in case of failure
            with self.lock:
                self.status["result"] = "Error"

            # Raise a CommandExecutionError with detailed information
            raise CommandExecutionError(
                command=full_command,
                return_code=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
            ) from e

        except Exception as e:
            # General error handling
            with self.lock:
                self.status["result"] = "Error"

            raise CommandExecutionError(
                command=full_command,
                return_code=-1,
                stdout="",
                stderr=str(e),
            ) from e
