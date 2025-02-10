import os
import subprocess

import yaml


class SocatManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.base_dir, "socat_config.yaml")
        self.config = self.load_config()

    def run_command(self, command):
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {command}")
            print(f"Return code: {e.returncode}")
            print(f"Output: {e.stdout.strip()}")
            print(f"Error: {e.stderr.strip()}")
            return ""

    def ensure_socat_installed(self):
        print("Checking if socat is installed...")
        installed = self.run_command("dpkg -l | grep -w socat")
        if not installed:
            print("Socat is not installed. Installing...")
            self.run_command("sudo apt update && sudo apt install -y socat")
        else:
            print("Socat is already installed.")

    def check_socat_running(self):
        print("Checking if socat is running...")
        result = self.run_command("sudo pgrep -x socat")
        return bool(result)

    def stop_socat(self):
        if self.check_socat_running():
            print("Stopping existing socat instances...")
            self.run_command("sudo pkill socat")
        else:
            print("No running socat instances found.")

    def start_socat(self, config):
        options = ",".join(config['options']) if isinstance(config['options'], list) else config['options']
        command = f"sudo socat TCP-LISTEN:{config['listen_port']},{options} TCP:{config['forward_host']}:{config['forward_port']}"
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Command: {command}")
        print("Socat started successfully.")

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Configuration file {self.config_file} not found.")
            return {}

    def setup(self):
        self.ensure_socat_installed()
        self.stop_socat()
        self.start_all_forwardings()

    def reload_config(self):
        self.config = self.load_config()
        self.stop_socat()
        self.start_all_forwardings()

    def start_all_forwardings(self):
        forwardings = self.config.get('forwardings', [])
        for forwarding_config in forwardings:
            self.start_socat(forwarding_config)
