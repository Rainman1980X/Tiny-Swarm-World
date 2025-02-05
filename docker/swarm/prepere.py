import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "multipass")))

from multipass.multipass_setup import MultipassSetup
from multipass.multipass_swarm_setup import MultipassSwarmSetup
from multipass.multipass_network_setup import MultipassNetworkSetup
from multipass.docker_install import DockerInstaller



class PrepareMultipass:
    def __init__(self):
        self.multipassSetup = MultipassSetup()
        self.multipasSwarmSetup = MultipassSwarmSetup()
        self.multipasDockerSetup = DockerInstaller()
        self.multipassNetworkSetup = MultipassNetworkSetup()

    def run (self):
        self.multipassSetup.full_setup()
        self.multipasSwarmSetup.full_setup()
        self.multipassNetworkSetup.setup_persistent_network()
        self.multipasDockerSetup.install_on_all_nodes()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("🔹 This script requires administrator privileges. Restarting with sudo...")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

    prepareMultipass = PrepareMultipass()
    prepareMultipass.run()