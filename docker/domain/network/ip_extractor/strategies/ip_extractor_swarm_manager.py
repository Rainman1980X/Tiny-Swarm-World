from typing import Optional

from domain.network.ip_extractor.strategies.ip_extractor_strategy import ExtractionStrategy
from infrastructure.logging.logger_factory import LoggerFactory


class IpExtractorSwarmManager(ExtractionStrategy):
    """Strategie zur Extraktion der Swarm-Manager-IP."""

    def __init__(self):
        self.logger = LoggerFactory.get_logger(self.__class__)

    def extract(self, result) -> Optional[str]:
        self.logger.info(f"Extracting gateway IP from: {result[1]}")
        return result[1][3].strip().split()[0]