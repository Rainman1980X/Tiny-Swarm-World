import os
import subprocess
import sys
import time


def wait_progress(duration):
    """Simple progress bar using stdout."""
    print(f"Waiting for {duration} seconds:")
    for i in range(duration):
        sys.stdout.write(f"\rProgress: {((i + 1) / duration) * 100:.0f}%")
        sys.stdout.flush()
        time.sleep(1)
    print("\rProgress: 100%")


def wait_for_multipass_socket(max_retries=10):
    """Checking Multipass socket if available"""
    print("Checking Multipass socket...")

    for attempt in range(max_retries):
        try:
            result = subprocess.run(["multipass", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True)
            if "No instances found" in result.stdout or result.returncode == 0:
                print(f"✅ Multipass is running!")
                return
        except subprocess.CalledProcessError:
            print(f"Attempt {attempt + 1}/{max_retries}: Multipass is not ready, retrying in 20 seconds...")
            wait_progress(20)

    print("❌ Multipass did not start correctly. Please check the Multipass service manually.")
    exit(1)


def restart_wsl():
    """Prompt to restart WSL for changes to take effect."""
    print("A restart of WSL is required. Please run the following command:")
    print("wsl --shutdown")


def is_multipass_installed():
    """Checks if Multipass is already installed."""
    try:
        result = subprocess.run(["multipass", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                check=True)
        print("✅ Multipass is already installed.")
        return True
    except subprocess.CalledProcessError:
        print("❌ Multipass is not installed.")
        return False


def run_command(command):
    """Executes a shell command and returns the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error while executing: {command}\n{e.stderr}")
        return None


def install_multipass():
    """Installs Multipass via Snap."""
    if is_multipass_installed():
        return
    print("Installing Multipass...")
    run_command("sudo snap install multipass")
    print("Multipass successfully installed.")


class MultipassSetup:
    def __init__(self, username=None):
        """Initialize the setup with the current user."""
        self.username = username or os.getenv("USER")

    def configure_multipass_group(self):
        """Creates the Multipass group and sets the correct permissions."""
        print("Checking if the 'multipass' group exists...")
        groups = run_command("getent group")
        if "multipass" not in groups:
            print("Creating the 'multipass' group...")
            run_command("sudo groupadd multipass")
        else:
            print("'multipass' group already exists.")

        print(f"Adding {self.username} to the 'multipass' group...")
        run_command(f"sudo usermod -aG multipass {self.username}")

        print("Setting correct permissions for the Multipass socket...")
        run_command("sudo chown root:multipass /var/run/multipass_socket || true")
        run_command("sudo chmod 660 /var/run/multipass_socket || true")

        print("Setting a Multipass passphrase (example, not secure!)")
        run_command("sudo multipass set local.passphrase='YourSecurePassword'")

    def setup(self):
        """Runs all setup steps."""
        install_multipass()
        self.configure_multipass_group()
        restart_wsl()
        print("Setup completed.")
        print("Waiting for Multipass service to start...")
        wait_for_multipass_socket()
