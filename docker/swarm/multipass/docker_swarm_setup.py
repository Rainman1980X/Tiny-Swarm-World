import subprocess
import time
from tqdm import tqdm


class DockerSwarmSetup:
    def __init__(self, manager_node="swarm-manager", worker_prefix="swarm-worker", worker_count=2):
        self.manager_node = manager_node
        self.worker_prefix = worker_prefix
        self.worker_count = worker_count
        self.swarm_token = ""
        self.swarm_manager_ip = ""

    def run_command(self, command, error_message):
        try:
            subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"{error_message}\n{e.stderr}")
            exit(1)

    def create_instance(self, name):
        print(f"Creating instance: {name}...")
        self.run_command(f"multipass launch -n {name} --memory 2G --disk 10G ",
                         f"Error: Failed to create instance {name}.")

    def setup_manager(self):
        print("\nSetting up Swarm Manager...")
        self.create_instance(self.manager_node)

        print("Initializing Docker Swarm...")
        self.run_command(f"multipass exec {self.manager_node} -- docker swarm init",
                         "Error: Failed to initialize Docker Swarm.")

        self.swarm_manager_ip = subprocess.run(f"multipass exec {self.manager_node} -- hostname -I | awk '{{print $1}}'",
                                               shell=True, check=True, text=True, capture_output=True).stdout.strip()

        self.swarm_token = subprocess.run(f"multipass exec {self.manager_node} -- docker swarm join-token -q worker",
                                          shell=True, check=True, text=True, capture_output=True).stdout.strip()

        print(f"Swarm Manager {self.manager_node} initialized at {self.swarm_manager_ip}")
        print(f"Swarm Join Token: {self.swarm_token}")

    def setup_workers(self):
        print("\nCreating Worker Nodes...")

        for i in range(1, self.worker_count + 1):
            worker_node = f"{self.worker_prefix}-{i}"
            print(f"Creating Worker Node {worker_node}...")
            self.create_instance(worker_node)

            print(f"Joining {worker_node} to Swarm...")
            self.run_command(f"multipass exec {worker_node} -- docker swarm join --token {self.swarm_token} {self.swarm_manager_ip}:2377",
                             f"Error: Failed to add {worker_node} to Swarm.")

        print("\nAll Worker Nodes successfully added to the Swarm Cluster!")

    def show_swarm_status(self):
        print("\nChecking Swarm Status...")
        self.run_command(f"multipass exec {self.manager_node} -- docker node ls",
                         "Error: Failed to retrieve Swarm status.")

    def full_setup(self):
        self.setup_manager()
        self.setup_workers()
        self.show_swarm_status()
        print("\n✅ Docker Swarm Cluster Setup Completed!")


if __name__ == "__main__":
    swarm_setup = DockerSwarmSetup()
    swarm_setup.full_setup()
