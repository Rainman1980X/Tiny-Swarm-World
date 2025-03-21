from typing import Dict

from domain.command.command_builder.other_parameter.parameter_type import ParameterType


class CommandParameterBuilder:
    """
    A builder class to replace placeholders in command templates with provided parameter values.
    Ensures that only allowed keys from the ParameterType enum are used.
    """

    @staticmethod
    def validate_params(params: Dict[ParameterType, str]) -> None:
        """
        Validates that all provided keys exist in the ParameterType Enum.

        :param params: Dictionary with Enum keys and their corresponding values
        :raises ValueError: If an invalid parameter key is found
        """
        allowed_keys = {param for param in ParameterType}
        invalid_keys = [key for key in params if key not in allowed_keys]

        if invalid_keys:
            raise ValueError(f"Invalid parameter keys detected: {invalid_keys}")

    def substitute_command(self, command_template: str, params: Dict[ParameterType, str]) -> str:
        """
        Replaces placeholders in a command with the given parameters.

        :param command_template: String containing placeholders in the format {param}
        :param params: Dictionary with Enum keys and their corresponding values
        :return: The formatted command as a string
        """
        self.validate_params(params)  # Ensure only allowed keys are used
        string_params = {key.value: value for key, value in params.items()}

        return command_template.format(**string_params)
