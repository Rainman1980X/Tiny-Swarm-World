from adapters.command_runner.ansible_runner import AnsibleCommandRunner
from adapters.command_runner.async_command_runner import AsyncCommandRunner
from adapters.command_runner.multipass_command_runner import MultipassCommandRunner
from adapters.command_runner.rest_api_runner import RestApiCommandRunner
from domain.command.command_runner_type_enum import CommandRunnerType
from ports.port_command_runner import CommandRunner


class CommandRunnerFactory:
    _runner_map = {
        CommandRunnerType.ASYNC: AsyncCommandRunner,
        CommandRunnerType.MULTIPASS: MultipassCommandRunner,
        CommandRunnerType.REST: RestApiCommandRunner,
        CommandRunnerType.ANSIBLE: AnsibleCommandRunner,
    }

    @staticmethod
    def get_runner(runner_type: CommandRunnerType) -> CommandRunner:
        runner_class = CommandRunnerFactory._runner_map.get(runner_type)
        if not runner_class:
            raise ValueError(f"Unsupported runner type: {runner_type}")
        return runner_class()
