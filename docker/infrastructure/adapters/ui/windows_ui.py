import os
import shutil

from application.ports.ui.port_ui import PortUI
import time

class WindowsUi(PortUI):
    def __init__(self, instances, test_mode=False):
        """test_mode: If True, the UI will exit after 2 seconds."""
        super().__init__(instances, test_mode)

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



    def _draw_ui(self):
        """
        Draws the UI in the Windows console.
        """
        previous_status = {instance: {"current_task": "", "current_step": "", "result": ""} for instance in
                           self.instances}

        while True:
            columns, _ = shutil.get_terminal_size()
            os.system("cls")  # Clear screen in Windows

            # Limit column width between 20 and 50 characters
            col_width = max(20, min(columns // len(self.instances), 50))

            # Header with instance names
            header = " | ".join(instance.center(col_width) for instance in self.instances)
            print(header)
            print("-" * len(header))

            changed = False
            with self.lock:
                rows = []
                for instance in self.instances:
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

                    # Format and truncate content if necessary
                    task_display = f"Task: {current_task[:col_width - 7]}".ljust(col_width)
                    step_display = f"Step: {current_step[:col_width - 7]}".ljust(col_width)
                    result_display = f"Status: {current_result[:col_width - 7]}".ljust(col_width)

                    rows.append([task_display, step_display, result_display])

                # Print rows
                for i in range(3):
                    print(" | ".join(row[i] for row in rows))

            time.sleep(0.5)

            # Check if all instances are completed
            if all(self.status[instance]["result"] in ["Success", "Error"] for instance in self.instances):
                print("\nAll instances completed".center(columns))
                time.sleep(2)
                break

            if self.test_mode:
                break

    def start(self):
        """
        Runs the console-based UI.
        """
        self._draw_ui()