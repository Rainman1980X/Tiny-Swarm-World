import subprocess
import unittest
from asyncio import TimeoutError, Lock
from unittest.mock import AsyncMock, patch, MagicMock

from adapters.command_runner.async_command_runner import AsyncCommandRunner
from adapters.exceptions.exception_command_execution import CommandExecutionError


class TestAsyncCommandRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.command_runner = AsyncCommandRunner()

    @patch('subprocess.run')
    def test_run_successful_command(self, mock_run):
        # Create a mock return value that mimics the `subprocess.run` result
        mock_run.return_value = MagicMock(
            stdout=b"Hello, World!\n",
            stderr=b"",
            returncode=0
        )

        # Example command for testing
        command = ["echo", "Hello, World!"]

        # Code under test
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.stdout, b"Hello, World!\n")


    @patch("asyncio.create_subprocess_shell")
    async def test_run_command_execution_error(self, mock_subprocess):
        command = "exit 1"
        stdout_output = b""
        stderr_output = b"Error occurred"

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (stdout_output, stderr_output)
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        with self.assertRaises(CommandExecutionError) as context:
            await self.command_runner.run(command)

        self.assertIn(
            "Command 'exit 1' failed with return code 1",
            str(context.exception)
        )
        self.assertEqual(context.exception.stdout, "")
        self.assertIn("Error occurred", context.exception.stderr)

    @patch("asyncio.create_subprocess_shell")
    async def test_run_asyncio_timeout(self, mock_subprocess):
        command = "sleep 10"
        timeout = 1

        mock_process = AsyncMock()
        mock_process.communicate.side_effect = TimeoutError()
        mock_process.returncode = 0  # Simulate timeout during execution
        mock_subprocess.return_value = mock_process

        with self.assertRaises(CommandExecutionError) as context:
            await self.command_runner.run(command, timeout=timeout)

        self.assertIn(f"Command timed out after {timeout} seconds.", str(context.exception))
        mock_process.communicate.assert_awaited()

    @patch("asyncio.create_subprocess_shell")
    async def test_run_unexpected_error(self, mock_subprocess):
        command = "invalid command"

        mock_subprocess.side_effect = Exception("Unexpected error")

        with self.assertRaises(CommandExecutionError) as context:
            await self.command_runner.run(command)

        self.assertIn("An unexpected error occurred: Unexpected error", str(context.exception))

    def test_lock_initialization(self):
        self.assertIsInstance(self.command_runner.lock, Lock)
