import re

from pydantic import BaseModel, field_validator


class IpValue(BaseModel):
    ip_address: str

    @field_validator("ip_address", mode="before")
    def validate_ip(cls, value: str) -> str:
        """Validates that the given value is a valid IPv4 address."""
        pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid IP address: {value}")
        return value
