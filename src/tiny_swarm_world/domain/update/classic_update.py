from __future__ import annotations

from dataclasses import dataclass
import re


_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
_IMAGE_REFERENCE = re.compile(r"^[^\s$`;&|<>]+$")

IMAGE_OVERRIDE_ENVIRONMENT_BY_STACK_SERVICE = {
    "traefik:traefik": "TSW_TRAEFIK_IMAGE",
    "nexus:nexus": "TSW_NEXUS_IMAGE",
    "jenkins:jenkins": "TSW_JENKINS_IMAGE",
    "pulsar:pulsar": "TSW_PULSAR_IMAGE",
    "pulsar:pulsar-manager": "TSW_PULSAR_MANAGER_IMAGE",
    "pulsar:pulsar-manager-bootstrap": "TSW_PULSAR_MANAGER_BOOTSTRAP_IMAGE",
    "service-access:service-access-dashboard": "TSW_SERVICE_ACCESS_DASHBOARD_IMAGE",
    "service-access:service-access-nginx": "TSW_SERVICE_ACCESS_NGINX_IMAGE",
    "infisical:infisical": "TSW_INFISICAL_IMAGE",
    "infisical:infisical-db": "TSW_INFISICAL_POSTGRES_IMAGE",
    "infisical:infisical-redis": "TSW_INFISICAL_REDIS_IMAGE",
}


def image_override_environment_name(stack_name: str, service_name: str) -> str:
    try:
        return IMAGE_OVERRIDE_ENVIRONMENT_BY_STACK_SERVICE[f"{stack_name}:{service_name}"]
    except KeyError as exc:
        raise ValueError(
            f"image update is unsupported for service '{service_name}' in stack '{stack_name}'"
        ) from exc


@dataclass(frozen=True)
class ClassicUpdatePlan:
    """A bounded, single-service image transition for an existing Classic stack."""

    stack_name: str
    service_name: str
    source_image: str
    target_image: str

    def __post_init__(self) -> None:
        for field_name in ("stack_name", "service_name"):
            value = getattr(self, field_name).strip()
            if not _IDENTIFIER.fullmatch(value):
                raise ValueError(f"{field_name} contains invalid characters")
            object.__setattr__(self, field_name, value)
        for field_name in ("source_image", "target_image"):
            value = getattr(self, field_name).strip()
            if not _IMAGE_REFERENCE.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe image reference")
            object.__setattr__(self, field_name, value)
        if self.source_image == self.target_image:
            raise ValueError("source_image and target_image must differ")

    @property
    def target_id(self) -> str:
        return f"update:{self.stack_name}:{self.service_name}"

    def to_dict(self) -> dict[str, str]:
        return {
            "service_name": self.service_name,
            "source_image": self.source_image,
            "stack_name": self.stack_name,
            "target_image": self.target_image,
        }

    @property
    def rollback_plan(self) -> ClassicUpdatePlan:
        return ClassicUpdatePlan(
            stack_name=self.stack_name,
            service_name=self.service_name,
            source_image=self.target_image,
            target_image=self.source_image,
        )


@dataclass(frozen=True)
class ClassicUpdateState:
    plan: ClassicUpdatePlan
    recorded_at: str
