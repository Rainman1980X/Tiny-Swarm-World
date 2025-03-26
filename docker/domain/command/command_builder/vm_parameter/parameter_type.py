from enum import Enum


class ParameterType(str, Enum):
    SWARM_MANAGER_IP = "swarm_manager_ip"
    SWARM_MANAGER_PORT = "swarm_manager_port"
    SWARM_TOKEN = "swarm_token"
