import subprocess


def run_command(command, **kwargs):
    """Executes a shell command and handles errors"""
    try:
        return subprocess.run(command, **kwargs)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {' '.join(command)}:", e)


class MultipassNetworkSetup:
    def __init__(self, instance_name="swarm-manager", interface="ens3",
                 template_file="multipass/cloud-init-template.yaml", output_file="cloud-init-manager.yaml"):
        """Initialize the network configuration for Multipass Swarm-Manager"""
        self.gateway = None
        self.ip_address = None
        self.instance_name = instance_name
        self.interface = interface
        self.template_file = template_file
        self.output_file = output_file
        self.target_path = f"/etc/netplan/{output_file.split('/')[-1]}"

    def get_swarm_manager_gateway(self):
        """Retrieves the default gateway of the swarm manager instance"""
        try:
            result = run_command(
                ["multipass", "exec", self.instance_name, "--", "ip", "-4", "route", "show", "default"],
                capture_output=True, text=True, check=True
            )
            output = result.stdout.strip().split()
            gateway = output[2] if len(output) > 2 else None
            return gateway
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving the gateway: {e}")
            return None

    def get_swarm_manager_ip_address(self):
        """Retrieves the current IP address of `swarm-manager` to be the static IP"""
        try:
            result = run_command(
                ["multipass", "exec", self.instance_name, "--", "hostname", "-I"],
                capture_output=True, text=True, check=True
            )
            ip_address = result.stdout.strip().split()[0] if result.stdout else None
            return ip_address
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving the IP address: {e}")
            return None

    def run_multipass_command(self, command):
        """Helper function to execute a command within the Multipass instance."""
        try:
            result = run_command(
                ["multipass", "exec", self.instance_name, "--"] + command,
                capture_output=True, text=True, check=True
            )
            print(f"Command executed successfully: {' '.join(command)}")
            print(result.stdout.strip())
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing {' '.join(command)}: {e}")
            return None

    def replace_template_variables(self):
        """Replaces the placeholders {{ADDRESS}} and {{GATEWAY}} in the cloud-config file."""
        if not self.ip_address or not self.gateway:
            print("Network data is missing, replacement not possible.")
            return

        try:
            with open(self.template_file, "r") as file:
                template_content = file.read()

            template_content = template_content.replace("{{ADDRESS}}", self.ip_address)
            template_content = template_content.replace("{{GATEWAY}}", self.gateway)

            with open(self.output_file, "w") as file:
                file.write(template_content)

            print(f"Replaced file saved under: {self.output_file}")

        except FileNotFoundError:
            print(f"The template file {self.template_file} was not found.")

    def setup(self):
        """Applies all configuration changes within the Multipass instance."""

        # Ensure IP address and gateway are retrieved before proceeding
        self.ip_address = self.get_swarm_manager_ip_address()
        self.gateway = self.get_swarm_manager_gateway()

        if not self.ip_address or not self.gateway:
            print("Network data is missing, netplan cannot be applied.")
            return

        # Generate the netplan.yaml file before applying the configuration
        self.replace_template_variables()

        try:
            # Step 1: Delete all existing netplan files
            self.run_multipass_command(["sudo", "rm", "-f", "/etc/netplan/*.yaml"])
            print("Old netplan configuration deleted.")

            # Step 2: Transfer the file to the instance
            subprocess.run(["multipass", "transfer", self.output_file, f"{self.instance_name}:/tmp/netplan.yaml"],
                           check=True)
            print("New netplan file transferred to Multipass instance.")

            # Step 3: Move the file to /etc/netplan
            self.run_multipass_command(["sudo", "mv", "/tmp/netplan.yaml", self.target_path])
            print(f"New netplan file moved to {self.target_path}.")

            # Step 4: Assign file ownership to root
            self.run_multipass_command(["sudo", "chown", "root:root", self.target_path])
            print(f"Ownership for {self.target_path} set to root.")

            # Step 5: Set permissions
            self.run_multipass_command(["sudo", "chmod", "600", self.target_path])
            print(f"Permissions for {self.target_path} set to 600.")

            # Step 6: Apply netplan
            self.run_multipass_command(["sudo", "netplan", "apply"])
            print("New netplan configuration has been applied.")

            # Step 7: Restart the swarm manager
            self.restart_instance()

        except subprocess.CalledProcessError as e:
            print(f"Error applying the network configuration: {e}")

    def restart_instance(self):
        """Restarts the Multipass instance."""
        try:
            subprocess.run(["multipass", "stop", self.instance_name], check=True)
            subprocess.run(["multipass", "start", self.instance_name], check=True)
            print(f"Instance {self.instance_name} successfully restarted.")

        except subprocess.CalledProcessError as e:
            print(f"Error restarting the instance {self.instance_name}: {e}")
