import re
import subprocess


class NetworkManager:
    def __init__(self, vm_name="swarm-manager", exposed_ports=None, internal_port=None):
        self.vm_name = vm_name
        self.exposed_ports = exposed_ports
        self.internal_port = internal_port
        self.windows_ip = self.get_windows_ip()
        self.wsl2_ip = self.get_wsl2_ip()
        self.multipass_ip = self.get_multipass_ip()

    def get_windows_ip(self):
        """Ermittelt die Windows-Host-IP unter WSL2."""
        result = subprocess.run(["sudo", "ip", "route"], capture_output=True, text=True)
        match = re.search(r"default via ([\d.]+)", result.stdout)
        return match.group(1) if match else None

    def get_wsl2_ip(self):
        """Ermittelt die WSL2-IP."""
        result = subprocess.run(["sudo", "hostname", "-I"], capture_output=True, text=True)
        return result.stdout.strip().split()[0] if result.stdout.strip() else None

    def get_multipass_ip(self):
        """Ermittelt die IP-Adresse der Multipass-VM."""
        result = subprocess.run(["sudo", "multipass", "info", self.vm_name], capture_output=True, text=True)
        match = re.search(r"IPv4:\s*([\d.]+)", result.stdout)
        return match.group(1) if match else None

    def setup_netsh_port_forwarding(self):
        print(f"🔄 Setze Windows-Portweiterleitung auf {self.wsl2_ip}:{self.exposed_ports}")
        subprocess.run(
            f"netsh interface portproxy add v4tov4 listenport={self.exposed_ports} listenaddress=0.0.0.0 connectport={self.exposed_ports} connectaddress={self.wsl2_ip}",
            shell=True)

    def setup_iptables_forwarding(self):
        """Setzt IPTables-Weiterleitung in WSL2 zu Multipass."""
        if not self.multipass_ip:
            print("Multipass-IP konnte nicht ermittelt werden!")
            return
        print(f"🔄 Setze IPTables-Weiterleitung zu Multipass ({self.multipass_ip}) für Port {self.exposed_ports}")
        subprocess.run(
            f"sudo iptables -t nat -A PREROUTING -p tcp --dport {self.exposed_ports} -j DNAT --to-destination {self.multipass_ip}:{self.internal_port}",
            shell=True)
        subprocess.run("echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward", shell=True)

    def configure_network(self):
        """Konfiguriert die Netzwerweiterleitungen."""
        print(f"🖥️ Windows-IP: {self.windows_ip}")
        print(f"🐧 WSL2-IP: {self.wsl2_ip}")
        print(f"🔗 Multipass-IP: {self.multipass_ip}")

        if self.wsl2_ip and self.multipass_ip:
            self.setup_iptables_forwarding()
            self.setup_netsh_port_forwarding()

        print("✅ Portweiterleitung abgeschlossen! Teste jetzt:")
        print(f"🔗 http://localhost:{self.exposed_ports}")


# Beispielaufruf
if __name__ == "__main__":
    manager = NetworkManager(exposed_ports=9000, internal_port=9000)  # Mehrere Ports
    manager.configure_network()
