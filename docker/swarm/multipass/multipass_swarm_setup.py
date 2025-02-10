import curses
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor


class MultipassSwarmSetup:
    def __init__(self, manager_node="swarm-manager", worker_prefix="swarm-worker", worker_count=2):
        """Initializes the Swarm VM setup."""
        self.manager_node = manager_node
        self.worker_prefix = worker_prefix
        self.worker_count = worker_count

        self.vm_list = [
            {"name": self.manager_node}
        ] + [
            {"name": f"{self.worker_prefix}-{i}"}
            for i in range(1, self.worker_count + 1)
        ]

        # Initialize status for each VM
        self.status = {vm["name"]: "Waiting..." for vm in self.vm_list}
        self.lock = threading.Lock()

    def run_command(self, command):
        """Executes a shell command."""
        subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def check_and_remove_existing_vm(self, vm_name):
        """Checks if a VM exists and deletes it if necessary."""
        result = subprocess.run(["multipass", "list"], capture_output=True, text=True)

        if vm_name in result.stdout:
            with self.lock:
                self.status[vm_name] = "Deleting..."

            self.run_command(f"multipass delete {vm_name}")
            self.run_command("multipass purge")

            # Wait until the VM is actually deleted
            max_retries = 10
            for attempt in range(max_retries):
                result = subprocess.run(["multipass", "list"], capture_output=True, text=True)
                if vm_name not in result.stdout:
                    break
                time.sleep(2)  # Wait time between checks

            with self.lock:
                self.status[vm_name] = "Deleted ✅"

    def create_instance(self, vm_name):
        """Creates a Multipass VM."""
        with self.lock:
            self.status[vm_name] = "Creating..."
        self.run_command(f"multipass launch -n {vm_name} --memory 2G --disk 10G ")
        with self.lock:
            self.status[vm_name] = "Done ✅"

    def setup_all_vms(self):
        """Handles the complete VM setup with real-time UI."""
        ui_thread = threading.Thread(target=self.run_ui)  # UI runs in parallel
        ui_thread.start()

        with ThreadPoolExecutor(max_workers=len(self.vm_list)) as executor:
            for vm in self.vm_list:
                vm_name = vm["name"]

                # 1️⃣ First check & delete, then wait
                executor.submit(self.check_and_remove_existing_vm, vm_name).result()
                time.sleep(3)  # Ensure Multipass is ready

                # 2️⃣ Then create the instance
                executor.submit(self.create_instance, vm_name)

        ui_thread.join()  # Wait until the UI is finished

    def run_ui(self):
        """Runs the live UI display for VM setup progress."""
        def draw_ui(stdscr):
            curses.curs_set(0)  # Hide cursor
            stdscr.nodelay(True)
            stdscr.timeout(500)  # Refresh every 500ms

            while True:
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                col_width = width // len(self.vm_list)

                # **Header (first row)**
                for idx, vm in enumerate(self.vm_list):
                    stdscr.addstr(0, idx * col_width, vm["name"].center(col_width), curses.A_BOLD)

                stdscr.addstr(1, 0, "-" * width)  # Separator line

                # **Live status for each VM**
                with self.lock:
                    for idx, vm in enumerate(self.vm_list):
                        stdscr.addstr(3, idx * col_width, f"Status: {self.status[vm['name']][:col_width - 7]}")

                stdscr.refresh()
                time.sleep(0.5)

                # **Exit condition: If all VMs are `✅ Done`, exit UI**
                if all(self.status[vm["name"]] == "Done ✅" for vm in self.vm_list):
                    time.sleep(2)  # Display final status for 2 seconds
                    break

        curses.wrapper(draw_ui)

    def setup(self):
        self.setup_all_vms()
        print("\nMultipass Swarm VM Setup Completed!")