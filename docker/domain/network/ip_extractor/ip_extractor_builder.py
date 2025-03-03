from domain.network.ip_extractor.strategies.ip_extractor_gateway import IpExtractorGateway
from domain.network.ip_extractor.strategies.ip_extractor_swarm_manager import IpExtractorSwarmManager
from domain.network.ip_extractor.strategies.ip_extstractor_types import IpExtractorTypes
from domain.network.ip_value import IpValue
from infrastructure.logging.logger_factory import LoggerFactory


class IpExtractorBuilder:

    def __init__(self):
        self.logger = LoggerFactory.get_logger(self.__class__)

        self.STRATEGY_MAP = {
            IpExtractorTypes.GATEWAY: IpExtractorGateway(),
            IpExtractorTypes.SWAM_MANAGER: IpExtractorSwarmManager(),
            IpExtractorTypes.NONE: None
        }

    def build(self, result:str, ip_extractor_types: IpExtractorTypes) -> IpValue:
        strategy = self.STRATEGY_MAP.get(ip_extractor_types)
        ip = IpValue(ip_address = "0.0.0.0")
        if strategy is not None:
            ip = IpValue(ip_address = strategy.extract(result))
        return ip
