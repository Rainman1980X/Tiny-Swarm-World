import subprocess
import unittest
from unittest.mock import patch, MagicMock

from docker.adapters.command_runner.multipass_command_runner import MultipassCommandRunner
from docker.adapters.exceptions.exception_command_execution import CommandExecutionError


class TestMultipassCommandRunner(unittest.TestCase):
    def setUp(self):
        self.instance_name = "test_instance"
        self.runner = MultipassCommandRunner(instance=self.instance_name)

    @patch("subprocess.run")
    def test_run_success(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "Expected output"
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        command = "echo 'Hello, World!'"
        result = self.runner.run(command)

        self.assertEqual(result, "Expected output")
        mock_subprocess_run.assert_called_once_with(
            f"multipass exec {self.instance_name} -- bash -c '{command}'",
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )

    @patch("subprocess.run")
    def test_run_failure(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_result.returncode = 127
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=127,
            cmd="command",
            output="",
            stderr="Command not found",
        )

        command = "unknown_command"

        with self.assertRaises(CommandExecutionError) as context:
            self.runner.run(command)

        self.assertIn("Command 'multipass exec", str(context.exception))
        self.assertIn("failed with return code 127", str(context.exception))

    @patch("subprocess.run", side_effect=Exception("Unexpected error"))
    def test_run_general_exception(self, mock_subprocess_run):
        command = "echo 'Unexpected failure'"

        with self.assertRaises(CommandExecutionError) as context:
            self.runner.run(command)

        self.assertIn("Unexpected error", str(context.exception))

    def test_instance_initialization(self):
        self.assertEqual(self.runner.instance, self.instance_name)
        self.assertIsInstance(self.runner.status, dict)
        self.assertIn("current_step", self.runner.status)
        self.assertIn("result", self.runner.status)

    @patch("subprocess.run")
    def test_status_lock_on_success(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.stdout = "Lock status test success"
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        command = "echo 'test'"
        self.runner.run(command)

        self.assertEqual(self.runner.status["result"], "Success")
        self.assertEqual(self.runner.status["current_step"], "Executing command")
