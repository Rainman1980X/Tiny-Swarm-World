import subprocess


class MultipassDockerSwarmSetup:
    def __init__(self, manager_node="swarm-manager", workers=None):
        if workers is None:
            workers = ["swarm-worker-1", "swarm-worker-2"]
        self.manager_node = manager_node
        self.workers = workers
        self.swarm_token = ""
        self.swarm_manager_ip = ""

    def run_command(self, command, error_message):
        try:
            result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"{error_message}\n{e.stderr}")
            exit(1)

    def setup_manager(self):
        print("\nInitializing Docker Swarm on Manager...")
        self.run_command(f"multipass exec {self.manager_node} -- docker swarm init",
                         "Error: Failed to initialize Docker Swarm.")

        self.swarm_manager_ip = self.run_command(
            f"multipass exec {self.manager_node} -- hostname -I | awk '{{print $1}}'",
            "Error: Failed to retrieve manager IP.")

        self.swarm_token = self.run_command(f"multipass exec {self.manager_node} -- docker swarm join-token -q worker",
                                            "Error: Failed to retrieve Swarm join token.")

        print(f"Swarm Manager initialized at {self.swarm_manager_ip}")
        print(f"Swarm Join Token: {self.swarm_token}")

    def setup_workers(self):
        print("\nJoining Worker Nodes to Swarm...")
        for worker in self.workers:
            self.run_command(
                f"multipass exec {worker} -- docker swarm join --token {self.swarm_token} {self.swarm_manager_ip}:2377",
                f"Error: Failed to add {worker} to Swarm.")
        print("All Worker Nodes successfully joined the Swarm.")

    def setup(self):
        self.setup_manager()
        self.setup_workers()
        print("\n✅ Swarm Setup Completed!")
