import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from docker.adapters.command_runner.async_command_runner import AsyncCommandRunner
from docker.adapters.exceptions.exception_command_execution import CommandExecutionError


class TestAsyncCommandRunner(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runner = AsyncCommandRunner()

    @patch("asyncio.create_subprocess_shell")
    async def test_run_successful_command(self, mock_subprocess):
        process_mock = AsyncMock()
        process_mock.communicate = AsyncMock(return_value=(b"output", b""))
        process_mock.returncode = 0
        mock_subprocess.return_value = process_mock

        result = await self.runner.run("echo test")
        self.assertEqual(result, "output")

    @patch("asyncio.create_subprocess_shell")
    async def test_run_command_execution_error(self, mock_subprocess):
        process_mock = AsyncMock()
        process_mock.communicate = AsyncMock(return_value=(b"", b"error"))
        process_mock.returncode = -1
        mock_subprocess.return_value = process_mock

        with self.assertRaises(CommandExecutionError) as cm:
            await self.runner.run("some_invalid_command")

        self.assertEqual(cm.exception.command, "some_invalid_command")
        self.assertEqual(cm.exception.returnCode, -1)
        self.assertEqual(cm.exception.stdout, "")
        self.assertIn("error", cm.exception.stderr)

    @patch("asyncio.create_subprocess_shell")
    @patch("asyncio.wait_for", side_effect=asyncio.TimeoutError)
    async def test_run_command_timeout(self, mock_wait_for, mock_subprocess):
        with self.assertRaises(CommandExecutionError) as cm:
            await self.runner.run("sleep 10", timeout=1)

        self.assertEqual(cm.exception.command, "sleep 10")
        self.assertEqual(cm.exception.returnCode, -1)
        self.assertEqual(cm.exception.stdout, "")
        self.assertIn("timed out", cm.exception.stderr)

    @patch("asyncio.create_subprocess_shell")
    @patch("asyncio.wait_for", side_effect=Exception("unexpected_error"))
    async def test_run_command_unexpected_exception(self, mock_wait_for, mock_subprocess):
        with self.assertRaises(CommandExecutionError) as cm:
            await self.runner.run("some_command")

        self.assertEqual(cm.exception.command, "some_command")
        self.assertEqual(cm.exception.returnCode, -1)
        self.assertEqual(cm.exception.stdout, "")
        self.assertIn("An unexpected error occurred", cm.exception.stderr)
