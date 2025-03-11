import asyncio

from application.services.multipass.multipass_docker_install import MultipassDockerInstall
from application.services.multipass.multipass_init_vms import MultipassInitVms
from application.services.multipass.multipass_restart_vms import MultipassRestartVMs
from application.services.network.network_service import NetworkService


async def main():
    multipass_init_vms = MultipassInitVms()
    await multipass_init_vms.run()

    network = NetworkService()
    await network.run()

    multipass_docker_install = MultipassDockerInstall()
    await multipass_docker_install.run()

    multipass_restart_vms = MultipassRestartVMs()
    await multipass_restart_vms.run()

    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
