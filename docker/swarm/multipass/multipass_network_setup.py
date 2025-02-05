import subprocess
import re

class MultipassNetworkSetup:
    def __init__(self, interface="ens3"):
        """Initialize the network configuration for Multipass Swarm-Manager"""
        self.interface = interface
        self.static_ip = self.get_current_ip()
        self.gateway = self.get_wsl_gateway()
        self.startup_script = "/etc/network-restart.sh"
        self.cron_file = "/etc/crontab"

    def get_wsl_gateway(self):
        """Retrieves the default gateway of the WSL2 instance"""
        try:
            result = subprocess.run(["ip", "route"], capture_output=True, text=True, check=True)
            for line in result.stdout.split("\n"):
                if line.startswith("default"):
                    return line.split()[2]
        except subprocess.CalledProcessError as e:
            print("❌ Error retrieving WSL2 gateway:", e)

        # Fallback gateway
        return "172.25.80.1"

    def get_current_ip(self):
        """Retrieves the current IP address of `swarm-manager` and converts it to a static IP"""
        try:
            print("🔍 Running command: multipass exec swarm-manager -- hostname -I")
            result = subprocess.run(["multipass", "exec", "swarm-manager", "--", "hostname", "-I"],
                                    capture_output=True, text=True, check=True)

            print(f"🔹 Command output: {result.stdout.strip()}")
            ip_address = result.stdout.strip().split()[0]  # Use the first IP address
            return f"{ip_address}/24" if ip_address else None
        except subprocess.CalledProcessError as e:
            print("❌ Error retrieving the current IP of swarm-manager:", e)
            return None

    def run_command(self, command):
        """Executes a shell command and handles errors"""
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error executing {' '.join(command)}:", e)

    def configure_network_interfaces(self):
        """Sets up the static IP using /etc/network/interfaces instead of Netplan"""
        if not self.static_ip:
            print("⚠️ No valid IP address found. Aborting.")
            return

        print(f"🔹 Setting static IP {self.static_ip} for swarm-manager with gateway {self.gateway}...")

        network_config = f"""auto {self.interface}
iface {self.interface} inet static
  address {self.static_ip.split('/')[0]}
  netmask 255.255.255.0
  gateway {self.gateway}
  dns-nameservers 8.8.8.8 8.8.4.4
"""

        # Write the new /etc/network/interfaces config
        self.run_command(["multipass", "exec", "swarm-manager", "--", "sudo", "bash", "-c", f"echo '{network_config}' > /etc/network/interfaces"])

        # Restart networking
        self.run_command(["multipass", "exec", "swarm-manager", "--", "sudo", "systemctl", "restart", "systemd-networkd"])

        print("✅ Static IP configured using /etc/network/interfaces!")

    def create_startup_script(self):
        """Creates a startup script inside the swarm-manager VM to configure the network at boot"""
        if not self.static_ip:
            print("⚠️ No valid IP address found. Aborting.")
            return

        print("🔹 Creating persistent network configuration script inside swarm-manager...")

        startup_script_content = f"""#!/bin/bash
sleep 5  # Ensure network is ready
ip addr flush dev {self.interface}
ip addr add {self.static_ip.split('/')[0]}/24 dev {self.interface}
ip route add default via {self.gateway}
"""

        # Write script inside the VM
        self.run_command(["multipass", "exec", "swarm-manager", "--", "sudo", "bash", "-c", f"echo '{startup_script_content}' > {self.startup_script}"])
        self.run_command(["multipass", "exec", "swarm-manager", "--", "sudo", "chmod", "+x", self.startup_script])

        print("✅ Network restart script created inside swarm-manager!")

        # Make it run on every boot using rc.local
        self.run_command(["multipass", "exec", "swarm-manager", "--", "sudo", "bash", "-c", "echo '@reboot root /etc/network-restart.sh' >> /etc/crontab"])

        print("✅ Added cron job to execute network script on every reboot!")

    def setup_persistent_network(self):
        """Ensures that the static IP is configured at every reboot"""
        self.configure_network_interfaces()
        self.create_startup_script()
        print("🚀 Persistent network configuration completed!")
