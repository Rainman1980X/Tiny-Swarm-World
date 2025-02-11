import uuid

from pydantic import BaseModel, Field


class VmEntity(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    vm_instance: str
    ipaddress: str = Field(default="")
    gateway: str = Field(default="")
