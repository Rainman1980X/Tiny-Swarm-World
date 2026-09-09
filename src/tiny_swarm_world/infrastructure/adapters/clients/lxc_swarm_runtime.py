from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Mapping

import requests
from tiny_swarm_world.application.ports.clients.port_swarm_stack_runtime import (
    PortSwarmStackRuntime,
    SwarmServiceStatus,
)
from tiny_swarm_world.application.ports.port_tls_contract_resolver import PortTlsContractResolver
from tiny_swarm_world.domain.deployment import StackDefinition
from tiny_swarm_world.domain.node_provider import ManagedLxcBackend
from tiny_swarm_world.infrastructure.adapters.clients.lxc.command.diagnostics import (
    is_transient_manager_shell_failure,
    safe_log_text,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.command.manager_shell_gateway import (
    LxcManagerShellGateway,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.docker.lxc_container_runtime import (
    LxcContainerRuntime,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.images.errors import (
    ImagePublisherOperationRejected as _ExtractedImagePublisherOperationRejected,
    PublicImagePullRejected as _ExtractedPublicImagePullRejected,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.images.lxc_container_image_publisher import (
    LxcContainerImagePublisher as _ExtractedLxcContainerImagePublisher,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_nexus_http_client import (
    LxcNexusHttpClient as _ExtractedLxcNexusHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.common import lxc_manager_ip
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_portainer_admin_client import (
    LxcPortainerAdminClient as _ExtractedLxcPortainerAdminClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_portainer_http_client import (
    LxcPortainerHttpClient as _ExtractedLxcPortainerHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.swarm.stack_asset_transfer import (
    StackAssetTransfer,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.swarm.stack_prerequisite_registry import (
    StackPrerequisiteRegistry,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.swarm import swarm_stack_runtime as _swarm_stack_runtime
from tiny_swarm_world.infrastructure.adapters.clients.lxc.swarm.swarm_stack_runtime import (
    LxcSwarmStackRuntime,
)
from tiny_swarm_world.infrastructure.logging.logger_factory import LoggerFactory
from tiny_swarm_world.infrastructure.process import ProcessRunner
from tiny_swarm_world.infrastructure.project_paths import ProjectPaths, default_project_paths


DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME = "tsw_traefik_tls_cert"
DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME = "tsw_traefik_tls_key"
DEFAULT_PORTAINER_ADMIN_SECRET_NAME = "tsw_portainer_admin_password"
INFISICAL_DATABASE_SERVICE_NAME = "infisical_infisical-db"
__all__ = [
    "ImagePublisherOperationRejected",
    "LxcContainerImagePublisher",
    "LxcContainerRuntime",
    "LxcNexusHttpClient",
    "LxcPortainerAdminClient",
    "LxcPortainerHttpClient",
    "LxcSwarmRuntime",
    "PublicImagePullRejected",
]


class LxcSwarmRuntime(PortSwarmStackRuntime):
    def __init__(
        self,
        *,
        backend: ManagedLxcBackend,
        manager_node: str = "swarm-manager",
        remote_stack_root: str = "/var/lib/tiny-swarm-world/stacks",
        timeout_seconds: int = 900,
        service_list_timeout_seconds: int = 30,
        project_paths: ProjectPaths | None = None,
        service_access_dashboard_renderer: Callable[[], str] | None = None,
        traefik_tls_cert_secret_name: str = DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
        traefik_tls_key_secret_name: str = DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
        portainer_admin_password: str | None = None,
        portainer_admin_secret_name: str = DEFAULT_PORTAINER_ADMIN_SECRET_NAME,
        shell_gateway: LxcManagerShellGateway | None = None,
        process_runner: ProcessRunner | None = None,
        tls_contract_resolver: PortTlsContractResolver,
    ):
        if timeout_seconds <= 0:
            raise ValueError("Swarm runtime timeout must be positive.")
        if service_list_timeout_seconds <= 0:
            raise ValueError("Swarm service list timeout must be positive.")
        if not traefik_tls_cert_secret_name.strip() or not traefik_tls_key_secret_name.strip():
            raise ValueError("Traefik TLS secret names must not be empty.")
        if portainer_admin_password is not None and not portainer_admin_password:
            raise ValueError("Portainer admin password must not be empty when configured.")
        if not portainer_admin_secret_name.strip():
            raise ValueError("Portainer admin secret name must not be empty.")
        self.backend = backend
        self.manager_node = manager_node
        self.remote_stack_root = remote_stack_root.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.service_list_timeout_seconds = service_list_timeout_seconds
        self.project_paths = project_paths or default_project_paths()
        self.service_access_dashboard_renderer = service_access_dashboard_renderer
        self.traefik_tls_cert_secret_name = traefik_tls_cert_secret_name.strip()
        self.traefik_tls_key_secret_name = traefik_tls_key_secret_name.strip()
        self.portainer_admin_password = portainer_admin_password
        self.portainer_admin_secret_name = portainer_admin_secret_name.strip()
        self.tls_contract_resolver = tls_contract_resolver
        self.logger = LoggerFactory.get_logger(self.__class__)
        self.process_runner = process_runner
        self.shell_gateway = shell_gateway or LxcManagerShellGateway(
            backend=backend,
            manager_node=manager_node,
            timeout_seconds=timeout_seconds,
            logger=self.logger,
            process_runner=process_runner,
        )
        self._stack_asset_transfer = StackAssetTransfer(
            project_paths=self.project_paths,
            run_manager_shell=lambda *args, **kwargs: self._run_manager_shell(*args, **kwargs),
            render_service_access_dashboard=lambda: self._render_service_access_dashboard(),
        )
        self._stack_prerequisite_registry = StackPrerequisiteRegistry()
        self.swarm_stack_runtime = LxcSwarmStackRuntime(
            remote_stack_root=self.remote_stack_root,
            service_list_timeout_seconds=self.service_list_timeout_seconds,
            run_manager_shell=lambda *args, **kwargs: self._run_manager_shell(*args, **kwargs),
            run_node_shell=lambda *args, **kwargs: self._run_node_shell(*args, **kwargs),
            prepare_stack_assets=lambda stack_name, _remote_dir: self.prepare_stack_assets(stack_name),
            ensure_stack_prerequisites=lambda stack_name, definition: self._ensure_stack_prerequisites(
                stack_name,
                definition,
            ),
            external_secret_exists=lambda name: self.external_secret_exists(name),
        )

    def prepare_stack_assets(self, stack_name: str) -> None:
        remote_dir = f"{self.remote_stack_root}/{stack_name}"
        self._transfer_stack_assets(stack_name, remote_dir)

    def deploy_stack(
        self,
        stack_definition: StackDefinition,
        stack_environment: Mapping[str, str] | None = None,
    ) -> None:
        self.swarm_stack_runtime.deploy_stack(
            stack_definition,
            stack_environment=stack_environment,
        )

    def stack_exists(self, stack_name: str) -> bool:
        return self.swarm_stack_runtime.stack_exists(stack_name)

    def list_stack_services(self, stack_name: str) -> tuple[SwarmServiceStatus, ...]:
        return self.swarm_stack_runtime.list_stack_services(stack_name)

    def external_secret_exists(self, name: str) -> bool:
        return self.swarm_stack_runtime.external_secret_exists(name)

    def ensure_external_secret(self, name: str, value: str) -> None:
        self.swarm_stack_runtime.ensure_external_secret(name, value)

    def recover_infisical_migration_lock(self) -> bool:
        return self.swarm_stack_runtime.recover_infisical_migration_lock()

    def _ensure_stack_prerequisites(self, stack_name: str, stack_definition: StackDefinition) -> None:
        self._stack_prerequisite_registry.ensure(
            stack_name,
            stack_definition,
            ensure_external_overlay_network=lambda name: self._ensure_external_overlay_network(name),
            ensure_portainer_admin_secret=self._ensure_portainer_admin_secret,
            ensure_traefik_tls_secrets=lambda: self._ensure_traefik_tls_secrets(),
            run_manager_shell=lambda *args, **kwargs: self._run_manager_shell(*args, **kwargs),
        )

    def _ensure_portainer_admin_secret(self) -> None:
        if self.portainer_admin_password is None:
            return
        self.ensure_external_secret(
            self.portainer_admin_secret_name,
            self.portainer_admin_password,
        )

    def _ensure_traefik_tls_secrets(self) -> None:
        self._stack_prerequisite_registry.ensure_traefik_tls_secrets(
            self.traefik_tls_cert_secret_name,
            self.traefik_tls_key_secret_name,
            external_secret_exists=lambda name: self.external_secret_exists(name),
            run_manager_shell=lambda *args, **kwargs: self._run_manager_shell(*args, **kwargs),
            tls_contract_resolver=self.tls_contract_resolver,
        )

    def _ensure_external_overlay_network(self, name: str) -> None:
        self._stack_prerequisite_registry.ensure_external_overlay_network(
            name,
            run_manager_shell=lambda *args, **kwargs: self._run_manager_shell(*args, **kwargs),
        )

    def _reconcile_host_published_ports(self, stack_definition: StackDefinition) -> None:
        self.swarm_stack_runtime.reconcile_host_published_ports(stack_definition)

    def _published_ports(self, swarm_service_name: str) -> set[tuple[str, str, str, str]]:
        return self.swarm_stack_runtime.published_ports(swarm_service_name)

    def _transfer_stack_assets(self, stack_name: str, remote_dir: str) -> None:
        self._stack_asset_transfer.transfer_stack_assets(stack_name, remote_dir)

    def _render_service_access_dashboard(self) -> str:
        if self.service_access_dashboard_renderer is not None:
            return self.service_access_dashboard_renderer()
        from tiny_swarm_world.infrastructure.adapters.repositories.compose_file_repository_yaml import (
            ComposeFileRepositoryYaml,
        )

        return ComposeFileRepositoryYaml(
            project_paths=self.project_paths,
        ).render_service_access_dashboard()

    def _run_manager_shell(
        self,
        script: str,
        *,
        check: bool = True,
        input_text: str | None = None,
        timeout_seconds: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.shell_gateway.run_manager_shell(
            script,
            check=check,
            input_text=input_text,
            timeout_seconds=timeout_seconds,
            # Preserve the legacy module patch seam only for direct, uncomposed
            # construction. Composition injects the shared runner instead.
            run=subprocess.run if self.process_runner is None else None,
            sleep=time.sleep,
        )

    def _run_node_shell(
        self,
        node_name: str,
        script: str,
        *,
        check: bool = True,
        input_text: str | None = None,
        timeout_seconds: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.shell_gateway.run_node_shell(
            node_name,
            script,
            check=check,
            input_text=input_text,
            timeout_seconds=timeout_seconds,
            # Preserve the legacy module patch seam only for direct, uncomposed
            # construction. Composition injects the shared runner instead.
            run=subprocess.run if self.process_runner is None else None,
            sleep=time.sleep,
        )


def _lxc_manager_ip(
    backend: ManagedLxcBackend,
    manager_node: str,
    timeout_seconds: int,
) -> str:
    return lxc_manager_ip(
        backend,
        manager_node,
        timeout_seconds,
        run=subprocess.run,
        sleep=time.sleep,
    )


def _validate_local_http_scheme(scheme: str) -> str:
    normalized = scheme.strip().lower()
    if normalized not in {"http", "https"}:
        raise ValueError("Local service URL scheme must be 'http' or 'https'.")
    return normalized


def _local_service_url(scheme: str, host: str, port: int) -> str:
    return f"{scheme}://{host}:{port}"


def _external_overlay_network_names(stack_definition: StackDefinition) -> tuple[str, ...]:
    """Compatibility export for the extracted Swarm helper."""

    return _swarm_stack_runtime._external_overlay_network_names(stack_definition)


def _published_ports_from_json(value: str) -> set[tuple[str, str, str, str]]:
    """Compatibility export for the extracted Swarm helper."""

    return _swarm_stack_runtime._published_ports_from_json(value)


def _quote_remote_path(path: str) -> str:
    """Compatibility export used by the remaining image-publisher adapter."""

    return _swarm_stack_runtime._quote_remote_path(path)


class LxcPortainerAdminClient(_ExtractedLxcPortainerAdminClient):
    """Compatibility facade retaining the legacy manager-IP patch seam."""

    def __init__(
        self,
        *,
        backend: ManagedLxcBackend,
        manager_node: str = "swarm-manager",
        port: int = 10001,
        scheme: str = "http",
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            backend=backend,
            manager_node=manager_node,
            port=port,
            scheme=scheme,
            session=session,
            timeout_seconds=timeout_seconds,
            manager_ip_resolver=lambda resolved_backend, resolved_node, resolved_timeout: _lxc_manager_ip(
                resolved_backend,
                resolved_node,
                resolved_timeout,
            ),
        )


class LxcNexusHttpClient(_ExtractedLxcNexusHttpClient):
    """Compatibility facade retaining the legacy manager-IP patch seam."""

    def __init__(
        self,
        *,
        backend: ManagedLxcBackend,
        manager_node: str = "swarm-manager",
        port: int = 13081,
        scheme: str = "http",
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(
            backend=backend,
            manager_node=manager_node,
            port=port,
            scheme=scheme,
            session=session,
            timeout_seconds=timeout_seconds,
            manager_ip_resolver=lambda resolved_backend, resolved_node, resolved_timeout: _lxc_manager_ip(
                resolved_backend,
                resolved_node,
                resolved_timeout,
            ),
        )


class LxcPortainerHttpClient(_ExtractedLxcPortainerHttpClient):
    """Compatibility facade retaining the legacy manager-IP patch seam."""

    def __init__(
        self,
        *,
        backend: ManagedLxcBackend,
        username: str,
        password: str,
        manager_node: str = "swarm-manager",
        port: int = 10001,
        scheme: str = "http",
        api_url: str | None = None,
        session: requests.Session | None = None,
        timeout_seconds: int = 30,
        stack_request_timeout_seconds: int = 180,
    ) -> None:
        super().__init__(
            backend=backend,
            username=username,
            password=password,
            manager_node=manager_node,
            port=port,
            scheme=scheme,
            api_url=api_url,
            session=session,
            timeout_seconds=timeout_seconds,
            stack_request_timeout_seconds=stack_request_timeout_seconds,
            manager_ip_resolver=lambda resolved_backend, resolved_node, resolved_timeout: _lxc_manager_ip(
                resolved_backend,
                resolved_node,
                resolved_timeout,
            ),
        )


LxcContainerImagePublisher = _ExtractedLxcContainerImagePublisher
PublicImagePullRejected = _ExtractedPublicImagePullRejected
ImagePublisherOperationRejected = _ExtractedImagePublisherOperationRejected


_is_transient_manager_shell_failure = is_transient_manager_shell_failure
_safe_log_text = safe_log_text
