import json
import os
import subprocess
import time

import requests


class PortainerSetup:
    def __init__(self):
        self.portainer_dir = os.path.dirname(os.path.abspath(__file__))
        self.swarm_manager_ip = self.get_swarm_manager_ip()

    def run_command(self, command):
        try:
            print(f"Executing: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error executing command: {command}\n{result.stderr}")
            return result.stdout.strip()
        except Exception as e:
            print(f"Exception: {e}")

    def get_swarm_manager_ip(self):
        print("Fetching Swarm Manager IP...")
        ip = self.run_command("multipass exec swarm-manager -- hostname -I").split()[0]
        print(f"Swarm Manager IP: {ip}")
        return ip

    def configure_iptables(self):
        print(f"Configuring iptables and socat for WSL2 on {self.swarm_manager_ip}...")

        print("Stopping any existing socat instances...")
        self.run_command("sudo pkill socat")

        print("Checking if iptables rule already exists...")
        existing_rule = self.run_command(
            f"sudo iptables -t nat -C PREROUTING -p tcp --dport 9000 -j DNAT --to-destination {self.swarm_manager_ip}:9000")
        if "No chain/target/match by that name" not in existing_rule and existing_rule:
            print("Removing existing iptables rule...")
            self.run_command(
                f"sudo iptables -t nat -D PREROUTING -p tcp --dport 9000 -j DNAT --to-destination {self.swarm_manager_ip}:9000")

        print("Starting socat in the background...")
        socat_result = self.run_command(
            f"nohup sudo socat TCP-LISTEN:9000,fork TCP:{self.swarm_manager_ip}:9000 > /dev/null 2>&1 &")
        if socat_result:
            print("Error starting socat. Check permissions and availability.")

        print("Adding iptables rule...")
        iptables_result = self.run_command(
            f"sudo iptables -t nat -A PREROUTING -p tcp --dport 9000 -j DNAT --to-destination {self.swarm_manager_ip}:9000")
        if "iptables: Bad rule" in iptables_result:
            print("Failed to add iptables rule. Check if the rule already exists.")
        else:
            print("iptables and socat configuration completed successfully.")

    def clean_docker(self):
        print("Cleaning up Docker system on Swarm Manager...")
        self.run_command(f"multipass exec swarm-manager -- docker system prune -a --volumes -f")
        self.run_command(f"multipass exec swarm-manager -- docker stack rm portainer")
        self.run_command(f"multipass exec swarm-manager -- docker system prune -a --volumes -f")
        self.run_command(
            f"multipass exec swarm-manager -- docker volume rm portainer_portainer_data || printf 'Volume not found or already deleted.\n'")
        self.run_command(f"multipass exec swarm-manager -- docker system prune -a --volumes -f")
        print("Cleanup completed.")

    def deploy_portainer(self):
        print("Deploying Portainer on Swarm Manager...")

        print("Ensuring directory exists on Multipass instance...")
        self.run_command("multipass exec swarm-manager -- mkdir -p /home/ubuntu/portainer")

        print("Transferring docker-compose.yml to Multipass instance...")
        self.run_command(
            f"multipass transfer {self.portainer_dir}/docker-compose.yml swarm-manager:/home/ubuntu/portainer/docker-compose.yml")

        print("Deploying Portainer stack...")
        self.run_command(
            "multipass exec swarm-manager -- docker stack deploy -c /home/ubuntu/portainer/docker-compose.yml portainer")

    def wait_for_portainer(self):
        print("Waiting for Portainer to start...")
        while True:
            try:
                response = requests.get(f"http://{self.swarm_manager_ip}:9000")
                if "Portainer" in response.text:
                    print("Portainer started successfully.")
                    break
            except requests.RequestException:
                pass
            print(".", end="", flush=True)
            time.sleep(5)

    def init_admin(self):
        print("Initializing Portainer admin user...")
        payload = json.dumps({
            "username": "admin",
            "password": "admin1234567890"
        })
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"http://{self.swarm_manager_ip}:9000/api/users/admin/init", headers=headers,
                                 data=payload)

        if response.status_code == 200:
            print("Admin account created successfully.")
        else:
            try:
                response_json = response.json()
                message = response_json.get("message", "Unknown error")
                details = response_json.get("details", "No details available")
                print(f"Error creating admin account: \n{{\"message\": \"{message}\", \"details\": \"{details}\"}}")
            except json.JSONDecodeError:
                print("Unexpected error response from Portainer.")

    def setup_portainer(self):
        self.configure_iptables()
        self.clean_docker()
        self.deploy_portainer()
        self.wait_for_portainer()
        self.init_admin()


if __name__ == "__main__":
    portainer_setup = PortainerSetup()
    portainer_setup.setup_portainer()
