# from docker.adapters.command_builder.command_builder import CommandBuilder
# from docker.adapters.command_runner.async_command_runner import AsyncCommandRunner
# from docker.adapters.command_runner.multipass_command_runner import MultipassCommandRunner
# from docker.adapters.repositories.command_multipass_init_repository_yaml import CommandRepositoryYaml
# from docker.adapters.repositories.vm_repository_yaml import VMRepositoryYaml
from application.multipass.multipass_init_vms import MultipassInitVms


def main():
    # # loading vm repository
    # vms_repository = VMRepositoryYaml()
    #
    # # loading command repository
    # # Runner for the bash
    # multipass_commandrunner = MultipassCommandRunner()
    # async_commandrunner = AsyncCommandRunner()
    #
    # multipass_command_repository = CommandRepositoryYaml(
    #     config_path="config/command_multipass_init_repository_yaml.yaml")
    #
    # # initialisation of multipass
    #
    # command_builder: CommandBuilder = CommandBuilder(
    #     command_repository=multipass_command_repository,
    #     vm_repository=vms_repository)
    #
    # commands = command_builder.get_command_list
    # print(commands)
    multipass_init_vms = MultipassInitVms()
    multipass_init_vms.run()

if __name__ == "__main__":
    main()
