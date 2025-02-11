from docker.adapters.yaml.netplan_configurator import NetplanConfigurationManager
from docker.application.network.network_service import NetworkService
from docker.domain.network.network import Network


def main():
    yaml_manager = NetplanConfigurationManager()
    network = NetworkService(yaml_manager)

    network_configuration = Network(ip_address="10.34.157.239", gateway="10.34.157.1", vm_instance="swarm-manager")

    network.run(network_configuration)


if __name__ == "__main__":
    main()
