from typing import Optional

from domain.network.ip_extractor.strategies.ip_extractor_strategy import ExtractionStrategy
from infrastructure.logging.logger_factory import LoggerFactory


class IpExtractorGateway(ExtractionStrategy):
    """Strategie zur Extraktion der Gateway-IP."""

    def __init__(self):
        self.logger = LoggerFactory.get_logger(self.__class__)

    def extract(self, result) -> Optional[str]:
        self.logger.info(f"Extracting gateway IP from: {result[1]}")
        value2 = result[1][2].strip().split()
        return value2[2] if len(value2) > 2 else None