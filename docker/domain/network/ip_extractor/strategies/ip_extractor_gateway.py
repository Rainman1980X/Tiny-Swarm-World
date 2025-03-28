import re
from typing import Union, Any

from domain.network.ip_extractor.strategies.ip_extractor_strategy import ExtractionStrategy
from domain.network.ip_value import IpValue
from infrastructure.logging.logger_factory import LoggerFactory


class IpExtractorGateway(ExtractionStrategy):
    """Strategy for extracting the gateway IP using regex."""

    def __init__(self):
        self.logger = LoggerFactory.get_logger(self.__class__)

    def extract(self, result: Union[dict, list]) -> Any:
        """
        Extracts the first valid IPv4 address from the dictionary entry with key 1.

        :param result: Dictionary or list containing network information
        :return: The first found IPv4 address as a string or None if no IP is found
        """
        # Handle cases where result is a list containing a dictionary
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
            result = result[0]

        if not isinstance(result, dict) or 1 not in result or not isinstance(result[1], str):
            self.logger.warning("Invalid input or missing key 1.")
            return None

        text = result[1].strip()
        self.logger.info(f"Extracting gateway IP from: {text}")

        # Regex pattern for IPv4 address
        match = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)

        if match:
            ip_address = match.group(0)
            self.logger.info(f"Found gateway IP: {ip_address}")
            return IpValue(ip_address =ip_address)

        self.logger.warning("No valid IP found.")
        return None  # Return None if no IP was found
