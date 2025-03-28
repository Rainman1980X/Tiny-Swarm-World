from pydantic import BaseModel
from domain.network.ip_value import IpValue

class DockerIpList(BaseModel):
    external_ip: IpValue
    docker_bridge_ip: IpValue
    docker_overlay_ip: IpValue
    gateway: IpValue
