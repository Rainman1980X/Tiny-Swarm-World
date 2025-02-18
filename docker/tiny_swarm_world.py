from docker.adapters.command_runner.async_command_runner import AsyncCommandRunner
from docker.adapters.command_runner.multipass_command_runner import MultipassCommandRunner
from docker.adapters.repositories.task_repository_yaml import TaskRepositoryYaml
from docker.adapters.repositories.vm_repository_yaml import VMRepositoryYaml
from docker.adapters.yaml.netplan_configurator import NetplanConfigurationManager
from docker.application.multipass.multipass_init_service import MultipassInitService
from docker.application.network.network_service import NetworkService
from docker.domain.network.network import Network


def main():
    # Runner for the bash
    multipass_commandrunner = MultipassCommandRunner("swarm-manager")
    async_commandrunner = AsyncCommandRunner()

    # loading config files
    task_repository = TaskRepositoryYaml(async_commandrunner=async_commandrunner,
                                         multipass_commandrunner=multipass_commandrunner)
    vms_repository = VMRepositoryYaml()

    # initialisation of multipass
    multipass_init_service: MultipassInitService = MultipassInitService(
        multipass_commandrunner=multipass_commandrunner,
        async_commandrunner=async_commandrunner,
        vms_repository=vms_repository
        , task_repository=task_repository)

    multipass_init_service.start_service()

    yaml_manager = NetplanConfigurationManager()
    network = NetworkService(yaml_manager)
    network_configuration = Network(ip_address="10.34.157.239", gateway="10.34.157.1", vm_instance="swarm-manager")

    network.run(network_configuration)


if __name__ == "__main__":
    main()
