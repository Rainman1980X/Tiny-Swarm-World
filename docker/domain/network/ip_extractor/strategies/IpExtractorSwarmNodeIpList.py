from typing import Optional, Any

from domain.network.docker_ip_list import DockerIpList
from domain.network.ip_extractor.strategies.ip_extractor_strategy import ExtractionStrategy
from domain.network.ip_value import IpValue
from infrastructure.logging.logger_factory import LoggerFactory


class IpExtractorSwarmNodeIpList(ExtractionStrategy):

    def __init__(self):
        self.logger = LoggerFactory.get_logger(self.__class__)

    def extract(self, result) -> DockerIpList:
        external_ip = IpValue(ip_address="1.1.1.1")
        docker_bridge_ip = IpValue(ip_address="1.1.1.1")
        docker_overlay_ip = IpValue(ip_address="1.1.1.1")
        gateway = IpValue(ip_address="1.1.1.1")

        return DockerIpList(external_ip=external_ip, docker_bridge_ip=docker_bridge_ip, docker_overlay_ip=docker_overlay_ip, gateway=gateway)