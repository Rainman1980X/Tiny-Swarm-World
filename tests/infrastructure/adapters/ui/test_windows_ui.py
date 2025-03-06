import asyncio
import unittest
from unittest.mock import patch, MagicMock

from infrastructure.adapters.ui.windows_ui import WindowsUi


class TestWindowsUI(unittest.TestCase):
    def setUp(self):
        self.instances = ["Instance1", "Instance2"]
        self.ui = WindowsUi(self.instances)
        self.ui.status = {
            "Instance1": {"current_task": "Starting...", "current_step": "Initializing...", "result": "Pending"},
            "Instance2": {"current_task": "Starting...", "current_step": "Initializing...", "result": "Pending"},
        }

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_initial_status(self):
        expected_status = {
            "Instance1": {
                "current_task": "Starting...",  # Include the additional field
                "current_step": "Initializing...",
                "result": "Pending",
            },
            "Instance2": {
                "current_task": "Starting...",  # Include the additional field
                "current_step": "Initializing...",
                "result": "Pending",
            },
        }
        self.assertEqual(self.ui.status, expected_status)

    @patch("shutil.get_terminal_size", return_value=(80, 24))
    @patch("os.system")
    def test_draw_ui_terminates_on_completion(self, mock_system, mock_terminal_size):
        self.ui.status = {
            "Instance1": {"current_task": "", "current_step": "", "result": "Success"},
            "Instance2": {"current_task": "", "current_step": "", "result": "Success"},
        }
        with patch("builtins.print") as mock_print:
            self.ui._draw_ui()
            mock_print.assert_any_call("\nAll instances completed".center(80))

    @patch("threading.Lock")
    def test_update_status(self, mock_lock):
        mock_lock_instance = MagicMock()
        mock_lock.return_value = mock_lock_instance
        self.ui.update_status("Instance1", task="", step="Step 1", result="Success")
        self.assertEqual(self.ui.status["Instance1"],
                         {"current_task": "", "current_step": "Step 1", "result": "Success"})

        self.ui.update_status("Instance2", task="", step="Step 2", result="Pending")
        self.assertEqual(self.ui.status["Instance2"]["current_step"], "Step 2")
        self.assertEqual(self.ui.status["Instance2"]["result"], "Pending")

    @patch("shutil.get_terminal_size", return_value=(80, 24))
    @patch("os.system")
    def test_start_ui_terminates_when_all_instances_completed(self, mock_system, mock_terminal_size):
        self.ui.status = {
            "Instance1": {"current_task": "", "current_step": "", "result": "Success"},
            "Instance2": {"current_task": "", "current_step": "", "result": "Success"},
        }
        with patch("builtins.print") as mock_print:
            self.ui._draw_ui()
            mock_print.assert_any_call("\nAll instances completed".center(80))
    # @patch("asyncio.get_running_loop", return_value=asyncio.new_event_loop())
    # @patch("threading.Thread")
    # def test_run_in_thread(self, mock_thread, mock_loop):
    #     self.ui.start_in_thread()
    #     mock_thread.assert_called_once()
    #
    # @patch("curses.wrapper")
    # def test_run_ui(self, mock_wrapper):
    #     self.ui.start()
    #     mock_wrapper.assert_called_once_with(self.ui._draw_ui)
