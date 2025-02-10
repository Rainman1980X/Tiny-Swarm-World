import curses
import subprocess
import threading
import time


class MultipassDockerInstaller:
    def __init__(self, manager_node="swarm-manager", worker_prefix="swarm-worker", worker_count=2):
        """Initializes the installation script for Docker on Ubuntu 24.04 LTS in Multipass VMs."""
        self.manager_node = manager_node
        self.worker_prefix = worker_prefix
        self.worker_count = worker_count
        self.instances = [self.manager_node] + [f"{self.worker_prefix}-{i}" for i in range(1, self.worker_count + 1)]
        self.status = {instance: {"current_step": "", "result": ""} for instance in self.instances}
        self.lock = threading.Lock()

    def run_command(self, instance, description, command):
        """Executes a shell command inside a Multipass VM with live updates."""
        full_command = f"multipass exec {instance} -- bash -c '{command}'"
        with self.lock:
            self.status[instance]["current_step"] = description
            self.status[instance]["result"] = "Running..."
        try:
            subprocess.run(full_command, shell=True, check=True, text=True, capture_output=True)
            with self.lock:
                self.status[instance]["result"] = "✔ Success"
        except subprocess.CalledProcessError:
            with self.lock:
                self.status[instance]["result"] = "✘ Error"
            exit(1)

    def install_docker_on_instance(self, instance_name):
        """Installs Docker on a specific Multipass VM."""
        commands = [
            ("Updating system", "sudo apt update > /dev/null 2>&1"),
            ("Upgrading system", "sudo apt upgrade -y > /dev/null 2>&1"),
            ("Installing required packages",
             "sudo apt install -y apt-transport-https ca-certificates curl software-properties-common > /dev/null 2>&1"),
            ("Ensuring GPG directory exists", "mkdir -p ~/.gnupg && chmod 700 ~/.gnupg"),
            ("Removing old Docker GPG key", "sudo rm -f /usr/share/keyrings/docker-archive-keyring.gpg"),
            ("Adding Docker GPG key",
             "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg"),
            ("Adding Docker repository",
             "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] "
             "https://download.docker.com/linux/ubuntu noble stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null"),
            ("Updating package list", "sudo apt update > /dev/null 2>&1"),
            ("Installing Docker",
             "sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1"),
            ("Enabling Docker service", "sudo systemctl enable --now docker"),
            ("Adding user 'ubuntu' to Docker group", "sudo usermod -aG docker ubuntu"),
            ("Applying group changes", "sudo su - ubuntu -c 'docker run hello-world'")
        ]
        for description, command in commands:
            self.run_command(instance_name, description, command)

    def setup(self):
        """Starts parallel Docker installation on all Multipass VMs with live UI."""
        threads = []
        for instance in self.instances:
            thread = threading.Thread(target=self.install_docker_on_instance, args=(instance,))
            threads.append(thread)
            thread.start()

        self.run_ui()

        for thread in threads:
            thread.join()

    def run_ui(self):
        """Runs the live UI display for installation progress."""
        def draw_ui(stdscr):
            curses.curs_set(0)  # Hide cursor
            stdscr.nodelay(True)
            stdscr.timeout(500)  # Refresh every 500ms

            while True:
                height, width = stdscr.getmaxyx()
                col_width = width // len(self.instances)

                # Print headers
                for idx, instance in enumerate(self.instances):
                    stdscr.addstr(0, idx * col_width, instance.center(col_width), curses.A_BOLD)

                # Print live status
                with self.lock:
                    for idx, instance in enumerate(self.instances):
                        stdscr.addstr(2, idx * col_width, f"Step: {self.status[instance]['current_step'][:col_width - 7]}")
                        stdscr.addstr(3, idx * col_width, f"Status: {self.status[instance]['result'][:col_width - 7]}")

                stdscr.refresh()
                time.sleep(0.5)

                # Exit condition: Check if all instances are finished
                if all(self.status[instance]["result"] in ["✔ Success", "✘ Error"] for instance in self.instances):
                    time.sleep(2)  # Let user see final state
                    break

        curses.wrapper(draw_ui)
