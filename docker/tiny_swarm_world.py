import asyncio

from application.services.multipass.multipass_docker_install import MultipassDockerInstall
from application.services.multipass.multipass_docker_swarm_init import MultipassDockerSwarmInit
from application.services.multipass.multipass_init_vms import MultipassInitVms
from application.services.multipass.multipass_restart_vms import MultipassRestartVMs
from application.services.network.network_prepare_netplan import NetworkPrepareNetplan
from application.services.network.network_service import NetworkService
from infrastructure.adapters.file_management.file_manager import FileManager
from infrastructure.adapters.file_management.path_strategies.path_factory import PathFactory
from infrastructure.dependency_injection.infra_core_di_container import infra_core_container
from infrastructure.logging.logger_factory import LoggerFactory


async def main():
    # Register FileManager explicitly


    #infra_core_container.scan_module("docker")
    infra_core_container.register(PathFactory)
    infra_core_container.register(FileManager)

    logger = LoggerFactory.get_logger("application")
    logger.info("Starting application")

    logger.info("MultipassInitVms")
    multipass_init_vms = MultipassInitVms()
    await multipass_init_vms.run()

    logger.info("NetworkPrepareNetplan")
    network_prepare_netplan = NetworkPrepareNetplan()
    await network_prepare_netplan.run()

    logger.info("NetworkService")
    network = NetworkService()
    await network.run()

    logger.info("MultipassRestartVMs")
    multipass_restart_vms = MultipassRestartVMs()
    await multipass_restart_vms.run()

    logger.info("MultipassDockerInstall")
    multipass_docker_install = MultipassDockerInstall()
    await multipass_docker_install.run()

    logger.info("MultipassRestartVMs")
    multipass_restart_vms = MultipassRestartVMs()
    await multipass_restart_vms.run()

    logger.info("MultipassDockerSwarmInit")
    multipass_restart_vms = MultipassDockerSwarmInit()
    await multipass_restart_vms.run()

    logger.info("Done")
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
