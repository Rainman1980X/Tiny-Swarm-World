import uuid

from pydantic import BaseModel, Field, field_validator

from domain.network.ip_value import IpValue


class Network(BaseModel):
    """Represents a network configuration with IP address, gateway, and VM instance."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    ip_address: IpValue
    gateway: IpValue
    vm_instance: str

    @field_validator("vm_instance", mode="before")
    def validate_vm_instance(cls, value: str) -> str:
        """Ensures that the VM instance name is not empty."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("VM instance cannot be empty")
        return value
