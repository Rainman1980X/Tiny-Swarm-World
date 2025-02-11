import re
import uuid

from pydantic import BaseModel, Field, field_validator


class Network(BaseModel):
    """Represents a network configuration with IP address, gateway, and VM instance."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    ip_address: str
    gateway: str
    vm_instance: str

    @field_validator("ip_address", "gateway", mode="before")
    def validate_ip(cls, value: str) -> str:
        """Validates that the given value is a valid IPv4 address."""
        pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if not re.match(pattern, value):
            raise ValueError(f"Invalid IP address: {value}")
        return value

    @field_validator("vm_instance", mode="before")
    def validate_vm_instance(cls, value: str) -> str:
        """Ensures that the VM instance name is not empty."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("VM instance cannot be empty")
        return value
