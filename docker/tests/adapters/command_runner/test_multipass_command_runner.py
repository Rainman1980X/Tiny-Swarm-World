import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from docker.adapters.command_runner.multipass_command_runner import MultipassCommandRunner
from docker.adapters.exceptions.exception_command_execution import CommandExecutionError


class TestMultipassCommandRunner(unittest.TestCase):
    def setUp(self):
        self.instance_name = "test-instance"
        self.runner = MultipassCommandRunner(self.instance_name)
        self.mock_process = MagicMock()
        # Kommunizieren async korrigiert
        self.mock_process.communicate = AsyncMock(return_value=(b"", b"Error output"))

    @patch("asyncio.create_subprocess_shell")
    def test_run_success(self, mock_subprocess_shell):
        self.mock_process.communicate = AsyncMock(return_value=(b"Expected output", b""))
        self.mock_process.returncode = 0
        mock_subprocess_shell.return_value = self.mock_process

        command = "echo 'Hello, World!'"
        result = asyncio.run(self.runner.run(command))
        self.assertEqual(result, "Expected output")
        mock_subprocess_shell.assert_called_once_with(
            f"multipass exec {self.instance_name} -- bash -c '{command}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    @patch("asyncio.create_subprocess_shell")
    def test_run_failure(self, mock_subprocess_shell):
        # Mock the process for a failing command
        self.mock_process.communicate = AsyncMock(return_value=(b"", b"Error output"))
        self.mock_process.returncode = 1  # Subprocess returns 1 for failure
        mock_subprocess_shell.return_value = self.mock_process

        command = "invalid command"
        with self.assertRaises(CommandExecutionError) as context:
            asyncio.run(self.runner.run(command))

        # Check that the error output is included in the raised exception
        self.assertIn("Error output", str(context.exception))

        # Validate that the expected returnCode is -1, based on the implementation
        self.assertEqual(context.exception.returnCode, -1)

        # Ensure that the correct command and context were passed to the subprocess
        mock_subprocess_shell.assert_called_once_with(
            f"multipass exec {self.instance_name} -- bash -c '{command}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    @patch("asyncio.create_subprocess_shell", side_effect=Exception("Unexpected error"))
    def test_run_general_exception(self, mock_subprocess_shell):
        command = "invalid command"
        with self.assertRaises(CommandExecutionError) as context:
            asyncio.run(self.runner.run(command))

        self.assertIn("Unexpected error", str(context.exception))
        self.assertEqual(context.exception.returnCode, -1)

    def test_instance_initialization(self):
        self.assertEqual(self.runner.instance, self.instance_name)
        self.assertIsNotNone(self.runner.lock)
        self.assertEqual(self.runner.status["current_step"], "Initialized")
        self.assertIsNone(self.runner.status["result"])

    @patch("asyncio.create_subprocess_shell")
    def test_status_lock_on_success(self, mock_subprocess_shell):
        # Mock the process for a successful command
        self.mock_process.communicate = AsyncMock(return_value=(b"Expected output", b""))
        self.mock_process.returncode = 0
        mock_subprocess_shell.return_value = self.mock_process

        # Mock the lock to support the context manager protocol
        self.runner.lock = MagicMock()
        self.runner.lock.__enter__.return_value = None
        self.runner.lock.__exit__.return_value = None

        command = "echo 'Success'"
        result = asyncio.run(self.runner.run(command))
        self.assertEqual(result, "Expected output")

        # Use the lock within the context
        with self.runner.lock:
            self.assertEqual(self.runner.status["result"], "Success")
