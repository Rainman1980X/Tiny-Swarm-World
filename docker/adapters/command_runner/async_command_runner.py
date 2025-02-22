import asyncio
import logging

from adapters.exceptions.exception_command_execution import CommandExecutionError
from ports.port_command_runner import CommandRunner


class AsyncCommandRunner(CommandRunner):
    """
    A class for asynchronously running shell commands and handling their outputs and errors.
    """

    def __init__(self):
        super().__init__()
        # Use asyncio.Lock for asynchronous operations
        self.lock = asyncio.Lock()
        # Initialisiere den Status als Dictionary (soweit nicht bereits in der Basisklasse geschehen)
        self.status = {"current_step": "Not started", "result": "Pending"}  # Default-Status
        self.logger = self.setup_logger()
        self.logger.info("AsyncCommandRunner initialized")

    def setup_logger(self):
        """
        Setzt einen klasseninstanzgebundenen Logger auf.
        Entfernt ggf. doppelte FileHandler.
        """
        logger = logging.getLogger(
            f"AsyncCommandRunner-{id(self)}")  # Einzigartiger Loggername basierend auf Instanz-ID
        logger.setLevel(logging.INFO)  # Loglevel: INFO

        # Entferne doppelte Handler
        if logger.hasHandlers():
            for handler in logger.handlers[:]:  # Kopie der Liste, um sicher zu iterieren
                if isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)

        # Datei-Handler hinzufügen, wenn keiner existiert
        file_handler = logging.FileHandler("async_command_runner.log", mode="a")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    async def run(self, command: str, timeout: int = None) -> str:
        self.logger.info(f"Starting subprocess: {command}")
        try:
            # Status aktualisieren
            async with self.lock:
                self.status["current_step"] = "Executing command"
                self.status["result"] = "Running..."

            # Loggen, dass der Prozess gestartet wird
            self.logger.info(f"Starting subprocess: {command}")

            # Starte Subprozess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Warte auf den Abschluss des Subprozesses
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            # Protokolliere die Ausgabe
            self.logger.info(f"Command output: {stdout.decode('utf-8').strip()}")

            # Überprüfen Sie den Rückgabecode des Prozesses
            if process.returncode != 0:
                error_message = stderr.decode('utf-8').strip()  # Fehler aus stderr lesen
                self.logger.error(f"Command failed with return code {process.returncode}: {error_message}")
                async with self.lock:
                    self.status["result"] = "Error"
                raise CommandExecutionError(
                    command=command,
                    return_code=process.returncode,
                    stdout=stdout.decode('utf-8').strip(),
                    stderr=error_message
                )

            # Aktualisiere den Status als erfolgreich
            async with self.lock:
                self.status["result"] = "Success"
            self.logger.info(f"Command completed successfully: {command}")

            return stdout.decode('utf-8').strip()

        except asyncio.TimeoutError:
            # Protokollieren, wenn ein Zeitüberschreitungsfehler auftritt
            async with self.lock:
                self.status["result"] = "Error"
            self.logger.error(f"Command timed out after {timeout} seconds: {command}")
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # -1 = Spezielle Rückkehr für Timeout
                stdout="",
                stderr=f"Command timed out after {timeout} seconds."
            )

        except Exception as e:
            # Protokolliere unerwartete Fehler
            self.logger.exception(f"An unexpected error occurred while executing the command: {command}")
            async with self.lock:
                self.status["result"] = "Error"
            raise CommandExecutionError(
                command=command,
                return_code=-1,  # -1 = Spezielle Rückkehr für unerwartete Fehler
                stdout="",
                stderr=f"An unexpected error occurred: {str(e)}"
            ) from e
