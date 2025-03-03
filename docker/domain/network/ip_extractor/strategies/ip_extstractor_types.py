from enum import Enum


class IpExtractorTypes(str, Enum):
    GATEWAY = "gateway"
    SWAM_MANAGER = "swarm-manager"
    NONE = "none"

    @staticmethod
    def get_enum_from_value(value: str) -> "IpExtractorTypes":
        for enum_member in IpExtractorTypes:
            if enum_member.value == value:
                return enum_member
        raise ValueError(f"Value '{value}' does not match any IpExtractorTypes.")
