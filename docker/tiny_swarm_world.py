import asyncio

from application.services.multipass.multipass_docker_install import MultipassDockerInstall
from application.services.multipass.multipass_docker_swarm_init import MultipassDockerSwarmInit
from application.services.multipass.multipass_init_vms import MultipassInitVms
from application.services.multipass.multipass_restart_vms import MultipassRestartVMs
from application.services.network.network_prepare_netplan import NetworkPrepareNetplan
from application.services.network.network_service import NetworkService
from infrastructure.logging.logger_factory import LoggerFactory


async def main():
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
