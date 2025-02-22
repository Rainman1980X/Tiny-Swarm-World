import asyncio

from application.multipass.multipass_init_vms import MultipassInitVms
from application.network.network_service import NetworkService


async def main():
    multipass_init_vms = MultipassInitVms()
    await multipass_init_vms.run()

    network = NetworkService()
    await network.run()

if __name__ == "__main__":
    asyncio.run(main())
