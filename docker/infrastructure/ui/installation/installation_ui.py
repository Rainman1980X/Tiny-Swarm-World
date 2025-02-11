import curses
import threading
import time


class InstallationUI:
    def __init__(self, instances):
        self.instances = instances
        self.status = {instance: {"current_step": "Initializing...", "result": "Pending"} for instance in instances}
        self.lock = threading.Lock()
        self.ui_thread = None

    def update_status(self, instance, step, result=None):
        """
        Updates the status of an instance.
        """
        with self.lock:
            if instance in self.status:
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

        previous_status = {instance: {"current_step": "", "result": ""} for instance in self.instances}

        while True:
            height, width = stdscr.getmaxyx()
            col_width = max(width // len(self.instances), 20)  # Set min width

            stdscr.clear()

            # Print headers
            for idx, instance in enumerate(self.instances):
                stdscr.addstr(0, idx * col_width, instance.center(col_width), curses.A_BOLD)

            changed = False
            with self.lock:
                for idx, instance in enumerate(self.instances):
                    current_step = self.status[instance]["current_step"]
                    current_result = self.status[instance]["result"]

                    if (previous_status[instance]["current_step"] != current_step or
                            previous_status[instance]["result"] != current_result):
                        changed = True
                        previous_status[instance]["current_step"] = current_step
                        previous_status[instance]["result"] = current_result

                    stdscr.addstr(2, idx * col_width, f"Step: {current_step[:col_width - 7]}")
                    stdscr.addstr(3, idx * col_width, f"Status: {current_result[:col_width - 7]}")

            if changed:
                stdscr.refresh()

            time.sleep(0.5)

            if all(self.status[instance]["result"] in ["✔ Success", "✘ Error"] for instance in self.instances):
                time.sleep(2)
                break

    def run_ui(self):
        """
        Runs the curses-based UI.
        """
        curses.wrapper(self._draw_ui)

    def run_in_thread(self):
        """
        Starts the UI in a separate thread.
        """
        self.ui_thread = threading.Thread(target=self.run_ui, daemon=True)
        self.ui_thread.start()
