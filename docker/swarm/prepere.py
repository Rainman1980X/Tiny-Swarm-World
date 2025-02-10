import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "multipass")))

from multipass.multipass_setup import MultipassSetup
from multipass.multipass_swarm_setup import MultipassSwarmSetup
from multipass.multipass_network_setup import MultipassNetworkSetup
from multipass.multipass_docker_setup import MultipassDockerInstaller
from multipass.multipass_docker_swarm_setup import MultipassDockerSwarmSetup
from multipass.multipass_socat_setup import SocatManager


class PrepareMultipass:
    def __init__(self):
        self.multipassSetup = MultipassSetup()
        self.multipassSwarmSetup = MultipassSwarmSetup()
        self.multipassDockerSetup = MultipassDockerInstaller()
        self.socatManager = SocatManager()
        self.multipassNetworkSetup = MultipassNetworkSetup()
        self.multipassDockerSwarmSetup = MultipassDockerSwarmSetup()

    def setup(self):
        # self.multipassSetup.setup()
        # self.multipassSwarmSetup.setup()
        self.multipassNetworkSetup.setup()
        # self.socatManager.setup()
        # self.multipassDockerSetup.setup()
        # self.multipassDockerSwarmSetup.setup()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script requires administrator privileges. Restarting with sudo...")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

    prepareMultipass = PrepareMultipass()
    prepareMultipass.setup()
