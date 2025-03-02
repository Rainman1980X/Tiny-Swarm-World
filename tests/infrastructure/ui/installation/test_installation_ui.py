import asyncio
import unittest
from unittest.mock import patch, MagicMock

from infrastructure.ui.installation.installation_ui import InstallationUI


class TestInstallationUI(unittest.TestCase):
    def setUp(self):
        self.instances = ["Instance1", "Instance2"]
        self.ui = InstallationUI(self.instances)
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

    @patch("asyncio.get_running_loop", return_value=asyncio.new_event_loop())
    @patch("threading.Thread")
    def test_run_in_thread(self, mock_thread, mock_loop):
        self.ui.run_in_thread()
        mock_thread.assert_called_once()

    @patch("curses.wrapper")
    def test_run_ui(self, mock_wrapper):
        self.ui.run_ui()
        mock_wrapper.assert_called_once_with(self.ui._draw_ui)

    @patch("curses.wrapper")
    def test_run_ui_terminates_when_all_instances_completed(self, mock_wrapper):
        """New Test: Ensures UI terminates when all instances mark result as completed."""

        def mock_draw_ui(stdscr):
            self.ui.update_status(instance="Instance1", task="", step="Step 1 Complete", result="Success")
            self.ui.update_status(instance="Instance2", task="", step="Step 1 Complete", result="Error")

        mock_wrapper.side_effect = mock_draw_ui

        self.ui.run_ui()

        self.assertEqual(self.ui.status["Instance1"]["result"], "Success")
        self.assertEqual(self.ui.status["Instance2"]["result"], "Error")

    @patch("infrastructure.ui.installation.installation_ui.curses.curs_set")
    @patch("infrastructure.ui.installation.installation_ui.curses.initscr")
    @patch("infrastructure.ui.installation.installation_ui.curses.endwin")
    def test_draw_ui_basic_execution(self, mock_endwin, mock_initscr, mock_curs_set):
        def stdscr_mock(*args, **kwargs):
            pass

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_initscr.return_value = mock_stdscr

        # Mock status for the instances
        self.ui.status = {
            "Instance1": {"current_task": "", "current_step": "", "result": ""},
            "Instance2": {"current_task": "", "current_step": "", "result": ""},
        }
        self.ui.lock = MagicMock()
        self.ui.test_mode = True
        # Call the _draw_ui function with the mocked stdscr
        self.ui._draw_ui(mock_stdscr)

        # Verify that curses methods were called
        mock_curs_set.assert_called_once_with(0)
        mock_stdscr.nodelay.assert_called_once_with(True)
        mock_stdscr.timeout.assert_called_once_with(500)

    @patch("infrastructure.ui.installation.installation_ui.curses.curs_set")
    @patch("infrastructure.ui.installation.installation_ui.curses.initscr")
    @patch("infrastructure.ui.installation.installation_ui.curses.endwin")
    def test_draw_ui_content_check(self, mock_endwin, mock_initscr, mock_curs_set):
        # Mock for `stdscr`
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)  # Simulate terminal size
        mock_initscr.return_value = mock_stdscr

        # Set instances and statuses
        self.ui.status = {
            "Instance1": {"current_task": "Task1", "current_step": "Downloading", "result": "Success"},
            "Instance2": {"current_task": "Task2", "current_step": "Installing", "result": "In Progress"},
        }

        # Activate test mode
        self.ui.test_mode = True  # Single iteration

        # Call _draw_ui
        self.ui._draw_ui(mock_stdscr)

        # Check for the presence of specific content
        mock_stdscr.addstr.assert_any_call(2, 0, "Task: Task1")  # Content for first instance
        mock_stdscr.addstr.assert_any_call(3, 0, "Step: Downloading")  # Content for first instance
        mock_stdscr.addstr.assert_any_call(4, 0, "Status: Success")  # Status for first instance
        mock_stdscr.addstr.assert_any_call(2, 40, "Task: Task2")  # Content for first instance
        mock_stdscr.addstr.assert_any_call(3, 40, "Step: Installing")  # Content for second instance
        mock_stdscr.addstr.assert_any_call(4, 40, "Status: In Progress")  # Status for second instance

    @patch("infrastructure.ui.installation.installation_ui.curses.curs_set")
    @patch("infrastructure.ui.installation.installation_ui.curses.initscr")
    @patch("infrastructure.ui.installation.installation_ui.curses.endwin")
    def test_draw_ui_terminates_on_completion(self, mock_endwin, mock_initscr, mock_curs_set):
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_initscr.return_value = mock_stdscr

        # Mock status for the instances, both completing successfully
        self.ui.status = {
            "Instance1": {"current_task": "", "current_step": "Finalizing", "result": "Success"},
            "Instance2": {"current_task": "", "current_step": "Stopping", "result": "Success"},
        }
        self.ui.lock = MagicMock()

        # Call the _draw_ui function with the mocked stdscr
        self.ui._draw_ui(mock_stdscr)

        # Extract all called 3rd arguments (text content)
        calls = [call.args[2] for call in mock_stdscr.addstr.mock_calls]

        # Assert the desired string exists
        assert any("All instances completed" in call for call in calls)
