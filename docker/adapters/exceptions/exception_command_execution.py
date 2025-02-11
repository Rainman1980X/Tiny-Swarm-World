class CommandExecutionError(Exception):
    """
    Custom exception for command execution errors.
    """

    def __init__(self, command: str, return_code: int, stdout: str, stderr: str):
        """
        Constructor for the CommandExecutionError class.

        Args:
            command (str): The command that was executed.
            return_code (int): The exit code of the command.
            stdout (str): The standard output of the command.
            stderr (str): The standard error output of the command.
        """
        super().__init__(f"Command '{command}' failed with return code {return_code}. Error: {stderr}")
        self.command = command
        self.returnCode = return_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        """
        Overrides the __str__() method to provide a meaningful string representation.
        """
        return (f"CommandExecutionError: Command '{self.command}' failed with return code {self.returnCode}\n"
                f"Stdout: {self.stdout}\nStderr: {self.stderr}")
