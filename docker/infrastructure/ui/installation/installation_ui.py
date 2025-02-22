import asyncio
import threading
import time
import platform
from concurrent.futures import ThreadPoolExecutor

if platform.system() == "Windows":
    try:
        import windows_curses
    except ImportError:
        import curses
       # print("Bitte installieren Sie 'windows-curses', um curses unter Windows zu nutzen.")
       # exit(1)
else:
    import curses

class InstallationUI:
    def __init__(self, instances, test_mode=False):
        """test_mode: If True, the UI will exit after 2 seconds."""
        self.instances = instances
        self.status = {instance: {"current_task": "Starting...", "current_step": "Initializing...", "result": "Pending"} for instance in instances}
        self.lock = threading.Lock()
        self.ui_thread = None
        self.test_mode = test_mode

    def update_status(self, instance, task, step, result=None):
        """
        Updates the status of an instance.
        """
        with self.lock:
            if instance in self.status:
                self.status[instance]["current_task"] = task
                self.status[instance]["current_step"] = step
                if result:
                    self.status[instance]["result"] = result

    def _draw_ui(self, stdscr):
        """
        Draws the UI using curses.
        """
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)
        stdscr.timeout(500)

        previous_status = {instance: {"current_task": "","current_step": "", "result": ""} for instance in self.instances}

        while True:
            height, width = stdscr.getmaxyx()

            # Begrenzen der Spaltenbreite zwischen 20 und 50 Zeichen
            col_width = max(20, min(width // len(self.instances), 50))

            stdscr.clear()

            # Check if the terminal is large enough
            if height < len(self.instances) + 5:
                stdscr.addstr(0, 0, f"Terminal too small ({height}x{width})!".center(width), curses.A_BOLD)
                stdscr.refresh()
                time.sleep(3)
                return

            # Print headers
            for idx, instance in enumerate(self.instances):
                stdscr.addstr(0, idx * col_width, instance.center(col_width), curses.A_BOLD)

            changed = False
            with self.lock:
                for idx, instance in enumerate(self.instances):
                    current_task = self.status[instance]["current_task"]
                    current_step = self.status[instance]["current_step"]
                    current_result = self.status[instance]["result"]

                    if (previous_status[instance]["current_step"] != current_step or
                            previous_status[instance]["result"] != current_result or
                            previous_status[instance]["current_task"] != current_task):
                        changed = True
                        previous_status[instance]["current_task"] = current_task
                        previous_status[instance]["current_step"] = current_step
                        previous_status[instance]["result"] = current_result

                    # Ensure content does not exceed column width
                    stdscr.addstr(2, idx * col_width, f"Task: {current_task[:col_width - 7]}")
                    stdscr.addstr(3, idx * col_width, f"Step: {current_step[:col_width - 7]}")
                    stdscr.addstr(4, idx * col_width, f"Status: {current_result[:col_width - 7]}")

            if changed:
                stdscr.refresh()

            time.sleep(0.5)

            # Handle successful completion of all instances
            if all(self.status[instance]["result"] in ["Success", "Error"] for instance in self.instances):
                # Ensure "All instances completed" fits within the terminal
                if len(self.instances) + 4 < height:
                    stdscr.addstr(len(self.instances) + 4, 0, "All instances completed".center(width)[:width],
                                  curses.A_BOLD)
                else:
                    # Print in the last line if there's no space
                    stdscr.addstr(height - 1, 0, "All instances completed".center(width)[:width], curses.A_BOLD)

                stdscr.refresh()
                if not self.test_mode:
                    time.sleep(2)
                    break

            if self.test_mode:
                break

    def run_ui(self):
        """
        Runs the curses-based UI.
        """
        curses.wrapper(self._draw_ui)

    def run_in_thread(self):
        """
          Starts the UI in a thread asynchronously using asyncio.
          """
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        self.ui_thread = loop.run_in_executor(executor, self.run_ui)


