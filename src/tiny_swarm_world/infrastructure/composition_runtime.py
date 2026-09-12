from __future__ import annotations

# This private module intentionally re-exports compatibility symbols consumed
# by the focused composition boundaries and legacy facade patch points.
# ruff: noqa: F401

import asyncio
import os
import shutil
import requests  # noqa: F401
import subprocess  # noqa: F401
from dataclasses import replace
from pathlib import Path
from typing import cast
from urllib.parse import urlparse
from uuid import uuid4

from tiny_swarm_world.application.ports.host import PortHostEnvironmentDetector
from tiny_swarm_world.application.ports.network import PortWslSocatExposure
from tiny_swarm_world.application.ports.method_trace import PortMethodTrace
from tiny_swarm_world.application.services.artifacts import (
    ArtifactPrepareStep,
    ArtifactPrepareWorkflow,
    ArtifactVerifyCheck,
    ArtifactVerifyWorkflow,
    ArtifactWorkflowKind,
    ArtifactReadinessGate,
    ArtifactWorkflowResult,
    EnsureContainerImage,
    EnsureNexusAdminAccess,
    EnsureNexusDockerHostedRepository,
    EnsureNexusDockerProxyRepository,
    EnsureNexusMavenProxyRepository,
    NexusDockerHostedRepositoryConfiguration,
    NexusDockerProxyRepositoryConfiguration,
    NexusMavenProxyRepositoryConfiguration,
    WaitForNexusReady,
    StaticArtifactContractPreflight,
)
from tiny_swarm_world.application.services.deployment import (
    DeploymentApplyWorkflow,
    DeploymentWorkflowKind,
    DeploymentVerifyWorkflow,
    EnsureInfisicalSilentInstall,
    EnsureInfisicalSecretItems,
    InfisicalSilentInstallConfig,
    EnsurePortainerEndpoint,
    EnsurePortainerAdminAccess,
    EnsureSonarqubeAdminAccess,
    EnsureSwarmStack,
    InfisicalSecretItem,
    InfisicalSecretSyncStep,
    SecretConsumptionVerifier,
    SecretDiscoveryStep,
    SecretEvidenceWriter,
    SecretManifestRenderer,
    WriteEffectiveAccessModelEvidence,
)
from tiny_swarm_world.application.services.deployment.workflows import (
    DeploymentApplyStep,
    DeploymentPreApplyStep,
)
from tiny_swarm_world.application.services.deployment.service_stack_plan import (
    DEFAULT_PORTAINER_ENDPOINT_NAME,
)
from tiny_swarm_world.application.ports.progress import PortWorkflowProgress
from tiny_swarm_world.application.ports.repositories.port_compose_file_repository import (
    PortComposeFileRepository,
)
from tiny_swarm_world.application.ports.ui.port_ui import (
    AGGREGATE_INSTANCE,
    STATUS_ERROR,
    PortUI,
)
from tiny_swarm_world.application.services.platform import (
    AsyncWorkflowStep,
    LxcDockerInstallService,
    LxcDockerInstallStep,
    LxcDockerVerifyStep,
    LxcProxyDriftRepairService,
    LxcProxyDriftRepairStep,
    LxcServiceExposureService,
    LxcServiceExposureStep,
    LxcServiceExposureVerifyStep,
    LxcSwarmBootstrapService,
    LxcSwarmBootstrapStep,
    LxcSwarmVerifyStep,
    NodeProviderDestroyManagedNodesStep,
    NodeProviderEnsureNodeStep,
    NodeProviderResetManagedNodesStep,
    NodeProviderSelectionRequest,
    NodeProviderSelectionService,
    NodeProviderVerifyNodeStep,
    PlatformDestroyWorkflow,
    PlatformExposeWorkflow,
    PlatformInitWorkflow,
    PlatformRepairLxcProxyDriftWorkflow,
    PlatformReconcileWorkflow,
    PlatformResetWorkflow,
    PlatformVerifyWorkflow,
    PortainerEndpointVerifyStep,
    PreflightService,
    SocatManager,
)
from tiny_swarm_world.application.services.platform.host import (
    AuthorizeProjectFilesystem,
    DetectHostEnvironment,
    EvaluateProjectFilesystem,
    HostPreparationAdapterFactory,
    HostPreparationService,
)
from tiny_swarm_world.infrastructure.adapters.file_management.local_file_storage import (
    LocalFileStorage,
)
from tiny_swarm_world.infrastructure.adapters.host import (
    HostEnvironmentDetector,
    ProjectFilesystemInspector,
)
from tiny_swarm_world.application.services.network import (
    NetworkDoctorService,
    NetworkRepairOptions,
    NetworkRepairService,
)
from tiny_swarm_world.application.services.configuration import ConfigurationValidationService
from tiny_swarm_world.application.services.setup import (
    SetupWorkflow,
    SetupWorkflowPhase,
    SetupWorkflowResult,
)
from tiny_swarm_world.domain.deployment import (
    ServiceStackContract,
    ServiceStackProfile,
    service_stack_contracts_for_profile,
)
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus
from tiny_swarm_world.domain.network.port_forwarding_plan import (
    ForwardingStrategy,
    PortForwardingPlan,
)
from tiny_swarm_world.domain.node_provider import (
    ManagedLxcBackend,
    NodeProviderKind,
    NodeRole,
    NodeSpec,
)
from tiny_swarm_world.domain.preflight import (
    PreflightResult,
    LiveConsent,
    PreflightConfiguration,
    ProviderPreflightMetadata,
    default_installation_plan,
    default_setup_manifest,
    default_preflight_configuration,
    default_resource_profiles,
    RequiredDependency,
    ResourceThresholds,
)
from tiny_swarm_world.infrastructure.adapters.command_runner.command_workflow import CommandWorkflow
from tiny_swarm_world.infrastructure.adapters.clients.lxc.command.backend_cli import backend_cli
from tiny_swarm_world.infrastructure.adapters.clients.lxc_node_provider import (
    AsyncLxcNodeCommandRunner,
    LxcNodeProvider,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc_container_docker_runtime import (
    LxcContainerDockerRuntime,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc_proxy_device_runtime import (
    LxcProxyDeviceRuntime,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.docker.lxc_container_runtime import (
    LxcContainerRuntime,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.images.lxc_container_image_publisher import (
    LxcContainerImagePublisher,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_nexus_http_client import (
    LxcNexusHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_portainer_admin_client import (
    LxcPortainerAdminClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.services.lxc_portainer_http_client import (
    LxcPortainerHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import LxcSwarmRuntime
from tiny_swarm_world.infrastructure.adapters.clients.infisical_playwright_client import (
    PlaywrightInfisicalClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.infisical_cli_client import (
    InfisicalCliClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.infisical_bootstrap_http_client import (
    InfisicalBootstrapHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.clients.sonarqube_http_client import (
    SonarqubeHttpClient,
)
from tiny_swarm_world.infrastructure.adapters.configuration import (
    CombinedConfigurationSource,
    EnvironmentConfigurationSource,
    ShellEnvFileConfigurationSource,
)
from tiny_swarm_world.infrastructure.adapters.ui.progress_trace_ui import (
    TerminalMethodTrace,
    TerminalWorkflowProgress,
)
from tiny_swarm_world.infrastructure.adapters.ui.factory_ui import FactoryUI
from tiny_swarm_world.infrastructure.adapters.preflight import (
    BoundedArtifactReadinessAdapter,
    DockerManagerReadinessProbe,
    HostPreflightProbe,
    HttpArtifactSourceReadiness,
    HttpEndpointReadinessProbe,
    LxcProviderPreflightProbe,
    LocalDirectoryReadinessProbe,
    ManagedLxcDirectoryReadinessProbe,
    ManagedLxcDockerManagerReadinessProbe,
    SecretStorageProbe,
    UnavailableArtifactReadinessProbe,
)
from tiny_swarm_world.infrastructure.adapters.host.wsl_resource_inspector import WslResourceInspector
from tiny_swarm_world.infrastructure.adapters.host.hang_diagnostics import ReadOnlyHangDiagnostics
from tiny_swarm_world.infrastructure.adapters.host.preflight_evidence_writer import PreflightEvidenceWriter
from tiny_swarm_world.infrastructure.adapters.network import (
    SubprocessNetworkProbe,
    SubprocessNetworkRepair,
    WslSocatExposureAdapter,
)
from tiny_swarm_world.infrastructure.adapters.repositories.compose_file_repository_yaml import (
    ComposeFileRepositoryYaml,
)
from tiny_swarm_world.infrastructure.adapters.repositories.node_provider_config_yaml_repository import (
    NodeProviderConfig,
    NodeProviderConfigYamlRepository,
)
from tiny_swarm_world.infrastructure.adapters.repositories.port_registry_yaml_repository import (
    PortRegistryYamlRepository,
)
from tiny_swarm_world.infrastructure.adapters.repositories.routing_evidence_local_repository import (
    RoutingEvidenceLocalRepository,
)
from tiny_swarm_world.infrastructure.adapters.repositories.project_filesystem_evidence_local_repository import (
    ProjectFilesystemEvidenceLocalRepository,
)
from tiny_swarm_world.infrastructure.os_types import OsTypes
from tiny_swarm_world.infrastructure.adapters.repositories.verification_evidence_local_repository import (
    VerificationEvidenceLocalRepository,
)
from tiny_swarm_world.infrastructure.logging.logger_factory import LoggerFactory
from tiny_swarm_world.infrastructure.logging.progress_trace_logging import (
    CompositeMethodTrace,
    CompositeWorkflowProgress,
    LoggingMethodTrace,
    LoggingWorkflowProgress,
)
from tiny_swarm_world.infrastructure.project_paths import ProjectPaths, default_project_paths
from tiny_swarm_world.infrastructure.process import ProcessRunner, SubprocessProcessRunner
from tiny_swarm_world.infrastructure.composition_blocked_workflows import (
    BlockedArtifactWorkflow,
    BlockedDeploymentWorkflow,
)
from tiny_swarm_world.infrastructure.composition_lxc_runtimes import (
    PrepareLxcStackAssets,
    ProviderSelectedLxcDockerRuntime,
    ProviderSelectedLxcProxyDeviceRuntime,
    ProviderSelectedLxcSwarmRuntime,
    selected_lxc_backend,
)
from tiny_swarm_world.infrastructure.composition_models import (
    ApplicationServices,
    ArtifactServices,
    ArtifactWorkflows,
    ClusterWorkflows,
    DeploymentServices,
    DeploymentWorkflows,
    PlatformServices,
    PlatformWorkflows,
    SetupServices,
    SetupWorkflows,
)

from tiny_swarm_world.infrastructure.composition_configuration import (
    DEFAULT_DEPLOYMENT_VERIFY_TIMEOUT_SECONDS,
    DEFAULT_INFISICAL_ORGANIZATION,
    DEFAULT_INFISICAL_READINESS_ATTEMPTS,
    DEFAULT_INFISICAL_READINESS_INTERVAL_SECONDS,
    DEFAULT_OPERATOR_CONFIGURATION_ENV_FILE,
    DEFAULT_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_PULSAR_IMAGE,
    DEFAULT_PULSAR_MANAGER_IMAGE,
    DEFAULT_SETUP_SERVICE_PROFILE,
    DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
    DEFAULT_TRAEFIK_GUI_USERS_SECRET_NAME,
    DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
    DEPLOYMENT_VERIFY_TIMEOUT_ENVIRONMENT,
    INFISICAL_ADMIN_FIRST_NAME_ENVIRONMENT,
    INFISICAL_ADMIN_LAST_NAME_ENVIRONMENT,
    INFISICAL_AUTH_SECRET_ENVIRONMENT,
    INFISICAL_ENCRYPTION_KEY_ENVIRONMENT,
    INFISICAL_IMAGE_ENVIRONMENT,
    INFISICAL_INTERNAL_URL_ENVIRONMENT,
    INFISICAL_LOGIN_EMAIL_ENVIRONMENT,
    INFISICAL_ORGANIZATION_ENVIRONMENT,
    INFISICAL_PASSWORD_ENVIRONMENT,
    INFISICAL_POSTGRES_IMAGE_ENVIRONMENT,
    INFISICAL_POSTGRES_PASSWORD_ENVIRONMENT,
    INFISICAL_READINESS_ATTEMPTS_ENVIRONMENT,
    INFISICAL_READINESS_INTERVAL_ENVIRONMENT,
    INFISICAL_REDIS_IMAGE_ENVIRONMENT,
    INFISICAL_REDIS_PASSWORD_ENVIRONMENT,
    JENKINS_IMAGE_ENVIRONMENT,
    NEXUS_IMAGE_ENVIRONMENT,
    PORTAINER_STACK_REQUEST_TIMEOUT_ENVIRONMENT,
    PULSAR_IMAGE_ENVIRONMENT,
    PULSAR_MANAGER_BOOTSTRAP_IMAGE_ENVIRONMENT,
    PULSAR_MANAGER_IMAGE_ENVIRONMENT,
    SEED_INFISICAL_ITEMS_ENVIRONMENT,
    SERVICE_ACCESS_DASHBOARD_IMAGE_ENVIRONMENT,
    SERVICE_ACCESS_NGINX_IMAGE_ENVIRONMENT,
    TRAEFIK_IMAGE_ENVIRONMENT,
    TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
    TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT,
    TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
    WINDOWS_EXPOSURE_ENVIRONMENT,
    _add_optional_config,
    _container_image_contracts_from_environment,
    _lxc_docker_apt_mirror_configuration,
    _lxc_docker_registry_mirror_configuration,
    _lxc_proxy_listen_address,
    _local_http_url,
    _nexus_docker_hub_proxy_port,
    _nexus_docker_hub_proxy_repository_name,
    _nexus_docker_proxy_remote_url,
    _operator_config_float,
    _operator_config_int,
    _operator_config_value,
    _operator_secret_value,
    _infisical_provider_mode,
    _self_hosted_infisical_url,
    _required_operator_secret_value,
    _swarm_registry_endpoint,
)
from tiny_swarm_world.infrastructure.composition_configuration import (  # noqa: F401
    DEFAULT_LXC_PROXY_LISTEN_ADDRESS,
)
from tiny_swarm_world.infrastructure.composition_probes import (
    EndpointReadinessCheck,
    _linux_text_file_equals as _probe_linux_text_file_equals,
)


_LOCAL_READINESS_SCHEME = "http"
DEFAULT_LXC_MANAGER_PROXY_PROFILE = "docker-swarm-manager"
DEFAULT_LXC_PLATFORM_NODES = (
    NodeSpec("swarm-manager", NodeRole.MANAGER, NodeProviderKind.LXC_NATIVE),
    NodeSpec("swarm-worker-1", NodeRole.WORKER, NodeProviderKind.LXC_NATIVE),
    NodeSpec("swarm-worker-2", NodeRole.WORKER, NodeProviderKind.LXC_NATIVE),
)
LXC_BACKEND_REQUIRED_REASON = "lxc_backend_required"
_LXC_SUPPORTED_BACKENDS = frozenset((ManagedLxcBackend.INCUS,))
LXC_BACKEND_REQUIRED_MESSAGE = (
    "LXC-native workflows require an available or explicitly selected Incus backend."
)
_BlockedArtifactWorkflow = BlockedArtifactWorkflow
_BlockedDeploymentWorkflow = BlockedDeploymentWorkflow
_ProviderSelectedLxcDockerRuntime = ProviderSelectedLxcDockerRuntime
_ProviderSelectedLxcSwarmRuntime = ProviderSelectedLxcSwarmRuntime
_PrepareLxcStackAssets = PrepareLxcStackAssets
_ProviderSelectedLxcProxyDeviceRuntime = ProviderSelectedLxcProxyDeviceRuntime
_selected_lxc_backend = selected_lxc_backend


class _BlockedPlatformProviderStep:
    returns_verification_result = True

    def __init__(
        self,
        *,
        target_id: str,
        provider_request: NodeProviderSelectionRequest,
        message: str,
        reason: str,
    ):
        self.verification_target_id = target_id
        self.provider_request = provider_request
        self.message = message
        self.reason = reason

    async def run(self) -> VerificationResult:
        await asyncio.sleep(0)
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.BLOCKED,
            message=self.message,
            evidence={
                "phase": "pre_apply",
                "reason": self.reason,
                "requested_provider": self.provider_request.requested_provider.value,
            },
        )


class _VerifiedPlatformProviderStep:
    returns_verification_result = True

    def __init__(
        self,
        *,
        target_id: str,
        provider_request: NodeProviderSelectionRequest,
        message: str,
        reason: str,
    ):
        self.verification_target_id = target_id
        self.provider_request = provider_request
        self.message = message
        self.reason = reason

    async def run(self) -> VerificationResult:
        await asyncio.sleep(0)
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.VERIFIED,
            message=self.message,
            evidence={
                "phase": "verify",
                "reason": self.reason,
                "requested_provider": self.provider_request.requested_provider.value,
            },
        )


class _WslSocatExposeStep:
    returns_verification_result = True
    verification_target_id = "platform:expose:wsl-socat"

    def __init__(
        self,
        socat_manager: SocatManager,
        socat_exposure: PortWslSocatExposure,
        *,
        service_profile: ServiceStackProfile,
        live_consent: LiveConsent | None,
        os_type: OsTypes | None = None,
    ) -> None:
        self.socat_manager = socat_manager
        self.socat_exposure = socat_exposure
        self.service_profile = service_profile
        self.live_consent = live_consent
        self.os_type = os_type

    async def run(self) -> VerificationResult:
        os_type = self.os_type or OsTypes.detect_current()
        plans = _wsl_socat_forwarding_plans(self.service_profile)
        commands = self.socat_manager.set_service_socat_ports(os_type, plans)
        if not commands:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.VERIFIED,
                message="WSL port exposure is not required for this host type.",
                evidence={
                    "phase": "verify",
                    "classification": "not_required",
                    "os_type": str(getattr(os_type, "value", os_type)),
                },
            )
        if self.live_consent is None or not self.live_consent.accepted:
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.BLOCKED,
                message="WSL port exposure requires accepted live infrastructure consent.",
                evidence={
                    "phase": "pre_apply",
                    "classification": "live_mutation_required",
                    "os_type": str(getattr(os_type, "value", os_type)),
                    "planned_forward_count": str(len(commands)),
                },
            )
        if not await self.socat_exposure.is_available():
            return VerificationResult(
                target_id=self.verification_target_id,
                status=VerificationStatus.VERIFIED,
                message="Optional WSL host port forwarding was skipped.",
                evidence={
                    "phase": "verify",
                    "classification": "socat_missing_skipped",
                    "os_type": str(getattr(os_type, "value", os_type)),
                    "planned_forward_count": str(len(commands)),
                    "remediation_hint": "Install the optional WSL forwarding tool and rerun platform expose when Windows-side forwarding is required.",
                },
            )

        started_count = 0
        existing_count = 0
        failed_count = 0
        for command in commands:
            pattern = command.shell_command
            if await self.socat_exposure.process_exists(pattern):
                existing_count += 1
                continue
            if await self.socat_exposure.start(pattern):
                started_count += 1
            else:
                failed_count += 1
        status = (
            VerificationStatus.VERIFIED
            if failed_count == 0
            else VerificationStatus.FAILED_TO_APPLY
        )
        return VerificationResult(
            target_id=self.verification_target_id,
            status=status,
            message=_wsl_socat_expose_message(status),
            evidence={
                "phase": "apply",
                "classification": (
                    "wsl_socat_exposed"
                    if status == VerificationStatus.VERIFIED
                    else "wsl_socat_expose_failed"
                ),
                "os_type": str(getattr(os_type, "value", os_type)),
                "planned_forward_count": str(len(commands)),
                "started_count": str(started_count),
                "existing_count": str(existing_count),
                "failed_count": str(failed_count),
            },
        )


def build_application_logger():
    return LoggerFactory.get_logger("application")


def build_host_environment_detector() -> HostEnvironmentDetector:
    return HostEnvironmentDetector()


def build_host_detection_service(
    detector: PortHostEnvironmentDetector | None = None,
) -> DetectHostEnvironment:
    return DetectHostEnvironment(detector or build_host_environment_detector())


def build_host_preparation_service(*args, **kwargs):
    from .composition_platform import build_host_preparation_service as implementation

    return implementation(*args, **kwargs)


def _build_native_linux_host_preparation():
    from tiny_swarm_world.infrastructure.adapters.host import NativeLinuxHostPreparation

    return NativeLinuxHostPreparation()


def _build_wsl_host_preparation(
    *,
    script_path: Path,
    config_path: Path,
    registry_path: Path,
    timeout_seconds: float,
):
    from tiny_swarm_world.infrastructure.adapters.host import (
        WindowsCommandRunner,
        WslHostPreparation,
    )

    return WslHostPreparation(
        WindowsCommandRunner(),
        script_path=script_path,
        config_path=config_path,
        port_registry_path=registry_path,
        timeout_seconds=timeout_seconds,
    )


def build_project_filesystem_inspector() -> ProjectFilesystemInspector:
    return ProjectFilesystemInspector()


def build_secret_storage_probe() -> SecretStorageProbe:
    return SecretStorageProbe(build_project_filesystem_inspector())


def _build_project_filesystem_services() -> tuple[
    EvaluateProjectFilesystem,
    AuthorizeProjectFilesystem,
]:
    inspector = build_project_filesystem_inspector()
    evidence_repository = ProjectFilesystemEvidenceLocalRepository.from_environment(
        os.environ,
        target_inspector=inspector,
    )
    return (
        EvaluateProjectFilesystem(inspector),
        AuthorizeProjectFilesystem(inspector, evidence_repository),
    )


def build_preflight_service(
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    configuration_validation: ConfigurationValidationService | None = None,
    allow_wsl_windows_filesystem: bool = False,
    include_secret_checks: bool = True,
    include_port_checks: bool = True,
) -> PreflightService:
    project_paths = default_project_paths()
    port_registry = PortRegistryYamlRepository(project_paths=project_paths).load()
    evaluator, authorizer = _build_project_filesystem_services()
    return PreflightService(
        HostPreflightProbe(
            project_paths=project_paths,
            host_environment_detector=build_host_environment_detector(),
            process_runner=build_process_runner(),
        ),
        _preflight_configuration_for_provider(service_profile, node_provider_request),
        configuration_validation=configuration_validation,
        port_registry=port_registry,
        project_filesystem_evaluator=evaluator,
        project_filesystem_authorizer=authorizer,
        project_path=project_paths.repository_root.as_posix(),
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        resource_inspector=WslResourceInspector(),
        evidence_writer=build_preflight_evidence_writer(),
        artifact_source_readiness=HttpArtifactSourceReadiness(),
        secret_storage_probe=build_secret_storage_probe(),
        secret_storage_path=_operator_configuration_env_file().as_posix(),
        require_existing_secret_storage_file=False,
        include_secret_checks=include_secret_checks,
        include_port_checks=include_port_checks,
    )


def build_configuration_validation_service(
    env_file: Path | None = None,
) -> ConfigurationValidationService:
    resolved_env_file = env_file or Path(
        os.environ.get("TSW_INSTALL_ENV_FILE", DEFAULT_OPERATOR_CONFIGURATION_ENV_FILE)
    )
    return ConfigurationValidationService(
        CombinedConfigurationSource(
            (
                ShellEnvFileConfigurationSource(resolved_env_file),
                EnvironmentConfigurationSource(),
            )
        )
    )


def _operator_configuration_env_file() -> Path:
    configured = os.environ.get("TSW_INSTALL_ENV_FILE", "").strip()
    return Path(configured) if configured else DEFAULT_OPERATOR_CONFIGURATION_ENV_FILE


def build_compose_file_repository(
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    environment: dict[str, str] | None = None,
) -> PortComposeFileRepository:
    return ComposeFileRepositoryYaml(
        project_paths=default_project_paths(),
        service_profile=service_profile,
        environment=environment,
    )


def build_network_doctor_service() -> NetworkDoctorService:
    project_paths = default_project_paths()
    port_registry = PortRegistryYamlRepository(project_paths=project_paths).load()
    return NetworkDoctorService(
        SubprocessNetworkProbe(
            host_environment_detector=build_host_environment_detector()
        ),
        port_registry,
    )


def build_read_only_hang_diagnostics() -> ReadOnlyHangDiagnostics:
    """Build the bounded, non-mutating workflow hang diagnostic adapter."""
    return ReadOnlyHangDiagnostics(
        timeout_seconds=_operator_config_float(
            "TSW_HANG_DIAGNOSTICS_TIMEOUT_SECONDS",
            10.0,
            minimum=0.1,
        )
    )


def build_preflight_evidence_writer() -> PreflightEvidenceWriter:
    configured = os.environ.get("TSW_LIVE_EVIDENCE_ROOT", "").strip()
    if configured:
        root = Path(configured).expanduser()
    else:
        configured_state = os.environ.get("XDG_STATE_HOME", "").strip()
        state_root = (
            Path(configured_state).expanduser()
            if configured_state
            else Path.home() / ".local" / "state"
        )
        root = state_root / "tiny-swarm-world" / "evidence" / "live-installation"
    return PreflightEvidenceWriter(root)


def build_process_runner() -> ProcessRunner:
    """Build the shared bounded infrastructure process runner."""
    return SubprocessProcessRunner()


def build_network_repair_service() -> NetworkRepairService:
    return NetworkRepairService(
        SubprocessNetworkProbe(
            host_environment_detector=build_host_environment_detector()
        ),
        SubprocessNetworkRepair(),
    )


def build_network_repair_options(
    *,
    runtime: str | None,
    linux_forwarding: bool,
    incus: bool,
    apply: bool,
) -> NetworkRepairOptions:
    return NetworkRepairOptions(
        runtime=runtime,
        linux_forwarding=linux_forwarding,
        incus=incus,
        apply=apply,
    )


def build_post_install_preflight_service(
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    configuration_validation: ConfigurationValidationService | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> PreflightService:
    project_paths = default_project_paths()
    configuration = _preflight_configuration_for_provider(service_profile, node_provider_request)
    evaluator, authorizer = _build_project_filesystem_services()
    return PreflightService(
        HostPreflightProbe(
            project_paths=project_paths,
            host_environment_detector=build_host_environment_detector(),
            process_runner=build_process_runner(),
        ),
        replace(configuration, required_ports=()),
        configuration_validation=configuration_validation,
        project_filesystem_evaluator=evaluator,
        project_filesystem_authorizer=authorizer,
        project_path=project_paths.repository_root.as_posix(),
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        resource_inspector=WslResourceInspector(),
        evidence_writer=build_preflight_evidence_writer(),
    )


def _build_workflow_progress_sink(ui: PortUI | None = None) -> PortWorkflowProgress:
    sinks: list[PortWorkflowProgress] = [
        LoggingWorkflowProgress(LoggerFactory.get_logger("WorkflowProgress"))
    ]
    if ui is not None:
        sinks.append(TerminalWorkflowProgress(ui))
    return CompositeWorkflowProgress(sinks)


def _build_method_trace_sink(ui: PortUI | None = None) -> PortMethodTrace:
    sinks: list[PortMethodTrace] = [
        LoggingMethodTrace(LoggerFactory.get_logger("MethodTrace"))
    ]
    if ui is not None:
        sinks.append(TerminalMethodTrace(ui))
    return CompositeMethodTrace(sinks)


def _new_installation_trace_correlation_id() -> str:
    return f"trace-installation-{uuid4().hex}"


def build_setup_ui(*, test_mode: bool = False) -> PortUI:
    return FactoryUI().get_ui(instances=(), test_mode=test_mode)


async def run_setup_with_terminal_status(*args, **kwargs):
    from .composition_setup import run_setup_with_terminal_status as implementation

    return await implementation(*args, **kwargs)


def _setup_result_status(result: SetupWorkflowResult) -> str:
    return result.status.value


def build_platform_services(*args, **kwargs):
    from .composition_platform import build_platform_services as implementation

    return implementation(*args, **kwargs)


def build_artifact_services_for_provider(*args, **kwargs):
    from .composition_artifacts import build_artifact_services_for_provider as implementation

    return implementation(*args, **kwargs)


def build_lxc_artifact_services(*args, **kwargs):
    from .composition_artifacts import build_lxc_artifact_services as implementation

    return implementation(*args, **kwargs)


def build_deployment_services_for_provider(*args, **kwargs):
    from .composition_deployment import build_deployment_services_for_provider as implementation

    return implementation(*args, **kwargs)


def build_lxc_deployment_services(*args, **kwargs):
    from .composition_deployment import build_lxc_deployment_services as implementation

    return implementation(*args, **kwargs)


def _build_artifact_readiness_gate(
    project_paths: ProjectPaths,
    node_provider_request: NodeProviderSelectionRequest | None = None,
) -> ArtifactReadinessGate:
    nexus_base_url = os.getenv(
        "TSW_NEXUS_READINESS_BASE_URL",
        f"{_LOCAL_READINESS_SCHEME}://127.0.0.1:13081",
    ).rstrip("/")
    registry_base_url = _http_readiness_base_url(_swarm_registry_endpoint())
    manager_storage_path = os.getenv("TSW_MANAGER_STORAGE_PATH", "/var/lib/docker")
    provider_request = node_provider_request or _default_node_provider_request()
    managed_backend = _artifact_readiness_backend(provider_request)
    if provider_request.requested_provider is not NodeProviderKind.LXC_NATIVE:
        docker_probe = DockerManagerReadinessProbe()
        storage_probe = LocalDirectoryReadinessProbe(
            Path(manager_storage_path),
            probe_kind="manager_storage",
        )
    elif managed_backend is None:
        docker_probe = UnavailableArtifactReadinessProbe(
            probe_kind="managed_lxc_docker_info",
        )
        storage_probe = UnavailableArtifactReadinessProbe(
            probe_kind="managed_lxc_directory",
        )
    else:
        docker_probe = ManagedLxcDockerManagerReadinessProbe(managed_backend)
        storage_probe = ManagedLxcDirectoryReadinessProbe(
            managed_backend,
            manager_storage_path,
        )
    return ArtifactReadinessGate(
        BoundedArtifactReadinessAdapter(
            {
                "docker:manager": docker_probe,
                "registry:endpoint": HttpEndpointReadinessProbe(
                    f"{registry_base_url}/v2/",
                    probe_kind="registry_endpoint",
                ),
                "nexus:endpoint": HttpEndpointReadinessProbe(
                    f"{nexus_base_url}/service/rest/v1/status",
                    probe_kind="nexus_endpoint",
                ),
                "nexus:repositories": HttpEndpointReadinessProbe(
                    f"{nexus_base_url}/service/rest/v1/repositories",
                    probe_kind="nexus_repositories",
                ),
                "storage:manager": storage_probe,
                "build:inputs": LocalDirectoryReadinessProbe(
                    project_paths.repository_root,
                    probe_kind="build_inputs",
                ),
                "pull:public": HttpEndpointReadinessProbe(
                    os.getenv(
                        "TSW_PUBLIC_PULL_READINESS_URL",
                        "https://registry-1.docker.io/v2/",
                    ),
                    probe_kind="public_pull",
                ),
            }
        )
    )


def _artifact_readiness_backend(
    provider_request: NodeProviderSelectionRequest,
) -> ManagedLxcBackend | None:
    if provider_request.requested_provider is not NodeProviderKind.LXC_NATIVE:
        return None
    if provider_request.preferred_backend is not None:
        return provider_request.preferred_backend
    if len(provider_request.backend_candidates) == 1:
        return provider_request.backend_candidates[0]
    return _lxc_backend_for_provider_request(provider_request)


def _http_readiness_base_url(endpoint: str) -> str:
    normalized = endpoint.strip()
    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"}:
        return normalized.rstrip("/")
    return f"{_LOCAL_READINESS_SCHEME}://{normalized.rstrip('/')}"


def build_setup_services(*args, **kwargs):
    from .composition_setup import build_setup_services as implementation

    return implementation(*args, **kwargs)


def build_classic_update_workflow(*args, **kwargs):
    from .composition_setup import build_classic_update_workflow as implementation

    return implementation(*args, **kwargs)


def build_application_services(*args, **kwargs):
    from .composition_setup import build_application_services as implementation

    return implementation(*args, **kwargs)


def _build_platform_services_for_request(
    service_profile: ServiceStackProfile | str,
    live_consent: LiveConsent | None,
    node_provider_request: NodeProviderSelectionRequest | None,
    ui: PortUI | None = None,
    trace_correlation_id: str | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> PlatformServices:
    if node_provider_request is None:
        if ui is None and trace_correlation_id is None:
            return build_platform_services(
                service_profile=service_profile,
                live_consent=live_consent,
                allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
            )
        return build_platform_services(
            service_profile=service_profile,
            live_consent=live_consent,
            ui=ui,
            trace_correlation_id=trace_correlation_id,
            allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        )
    if ui is None and trace_correlation_id is None:
        return build_platform_services(
            service_profile=service_profile,
            live_consent=live_consent,
            node_provider_request=node_provider_request,
            allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        )
    return build_platform_services(
        service_profile=service_profile,
        live_consent=live_consent,
        node_provider_request=node_provider_request,
        ui=ui,
        trace_correlation_id=trace_correlation_id,
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
    )


def _build_deployment_services_for_request(
    service_profile: ServiceStackProfile | str,
    node_provider_request: NodeProviderSelectionRequest | None,
    ui: PortUI | None = None,
    progress: PortWorkflowProgress | None = None,
) -> DeploymentServices:
    if ui is None:
        if progress is None:
            return build_deployment_services_for_provider(
                service_profile=service_profile,
                node_provider_request=node_provider_request,
            )
        return build_deployment_services_for_provider(
            service_profile=service_profile,
            node_provider_request=node_provider_request,
            progress=progress,
        )
    if progress is None:
        return build_deployment_services_for_provider(
            service_profile=service_profile,
            node_provider_request=node_provider_request,
            ui=ui,
        )
    return build_deployment_services_for_provider(
        service_profile=service_profile,
        node_provider_request=node_provider_request,
        ui=ui,
        progress=progress,
    )


def _build_preflight_service_for_request(
    service_profile: ServiceStackProfile | str,
    node_provider_request: NodeProviderSelectionRequest | None,
    configuration_validation: ConfigurationValidationService | None = None,
    project_paths: ProjectPaths | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> PreflightService:
    paths = project_paths or default_project_paths()
    if node_provider_request is None:
        node_provider_request = None
    port_registry = PortRegistryYamlRepository(project_paths=paths).load()
    evaluator, authorizer = _build_project_filesystem_services()
    return PreflightService(
        HostPreflightProbe(
            project_paths=paths,
            host_environment_detector=build_host_environment_detector(),
            process_runner=build_process_runner(),
        ),
        _preflight_configuration_for_provider(service_profile, node_provider_request),
        configuration_validation=configuration_validation,
        port_registry=port_registry,
        project_filesystem_evaluator=evaluator,
        project_filesystem_authorizer=authorizer,
        project_path=paths.repository_root.as_posix(),
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        resource_inspector=WslResourceInspector(),
        evidence_writer=build_preflight_evidence_writer(),
        artifact_source_readiness=HttpArtifactSourceReadiness(),
        secret_storage_probe=build_secret_storage_probe(),
        secret_storage_path=_operator_configuration_env_file().as_posix(),
        require_existing_secret_storage_file=False,
    )


def _build_post_install_preflight_service_for_request(
    service_profile: ServiceStackProfile | str,
    node_provider_request: NodeProviderSelectionRequest | None,
    configuration_validation: ConfigurationValidationService | None = None,
    project_paths: ProjectPaths | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> PreflightService:
    paths = project_paths or default_project_paths()
    configuration = _preflight_configuration_for_provider(service_profile, node_provider_request)
    evaluator, authorizer = _build_project_filesystem_services()
    return PreflightService(
        HostPreflightProbe(
            project_paths=paths,
            host_environment_detector=build_host_environment_detector(),
            process_runner=build_process_runner(),
        ),
        replace(configuration, required_ports=()),
        configuration_validation=configuration_validation,
        project_filesystem_evaluator=evaluator,
        project_filesystem_authorizer=authorizer,
        project_path=paths.repository_root.as_posix(),
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        secret_storage_probe=build_secret_storage_probe(),
        secret_storage_path=_operator_configuration_env_file().as_posix(),
        require_existing_secret_storage_file=False,
    )


def _lxc_backend_for_provider_request(
    provider_request: NodeProviderSelectionRequest,
) -> ManagedLxcBackend | None:
    if provider_request.requested_provider != NodeProviderKind.LXC_NATIVE:
        return None
    if provider_request.preferred_backend is not None:
        if provider_request.preferred_backend in _LXC_SUPPORTED_BACKENDS:
            return provider_request.preferred_backend
        return None
    for backend in provider_request.backend_candidates:
        if backend not in _LXC_SUPPORTED_BACKENDS:
            continue
        if shutil.which(backend_cli(backend)):
            return backend
    return None


def _default_node_provider_request() -> NodeProviderSelectionRequest:
    provider_config = NodeProviderConfigYamlRepository(
        project_paths=default_project_paths()
    ).load()
    return _node_provider_request_from_config(provider_config)


def _node_provider_request_from_config(
    provider_config: NodeProviderConfig,
) -> NodeProviderSelectionRequest:
    return NodeProviderSelectionRequest(
        requested_provider=provider_config.default_provider,
        preferred_backend=provider_config.preferred_backend,
        backend_candidates=provider_config.backend_candidates,
    )


def _preflight_configuration_for_provider(
    service_profile: ServiceStackProfile | str,
    node_provider_request: NodeProviderSelectionRequest | None,
) -> PreflightConfiguration:
    configuration = replace(
        default_preflight_configuration(service_profile=service_profile),
        windows_wsl_bridge_required=_windows_wsl_bridge_required(),
    )
    profile_name = (
        service_profile.value
        if isinstance(service_profile, ServiceStackProfile)
        else str(service_profile)
    )
    profiles = default_resource_profiles()
    resource_profile = profiles.get(profile_name, profiles["default"])
    configuration = replace(
        configuration,
        resources=ResourceThresholds(
            minimum_cpu_count=resource_profile.minimum.cpu_threads,
            minimum_memory_bytes=resource_profile.minimum.memory_bytes,
            minimum_disk_free_bytes=resource_profile.minimum.free_disk_bytes,
            disk_path=configuration.resources.disk_path,
        ),
    )
    provider_request = node_provider_request or _default_node_provider_request()
    if provider_request.requested_provider is not NodeProviderKind.LXC_NATIVE:
        return replace(
            configuration,
            provider_metadata=ProviderPreflightMetadata(
                provider=provider_request.requested_provider.value,
                generic_checks=configuration.provider_metadata.generic_checks,
            ),
        )
    backend = _lxc_backend_for_provider_request(provider_request)
    if backend is None:
        if not provider_request.backend_candidates:
            raise ValueError(
                "LXC-native preflight requires at least one managed backend candidate."
            )
        provider_dependencies = tuple(
            RequiredDependency(backend_cli(candidate))
            for candidate in provider_request.backend_candidates
        )
        backend_label = "auto"
        provider_checks = tuple(
            f"backend-cli:{backend_cli(candidate)}"
            for candidate in provider_request.backend_candidates
        )
    else:
        provider_dependencies = (RequiredDependency(backend_cli(backend)),)
        backend_label = backend.value
        provider_checks = (f"backend-cli:{backend_cli(backend)}",)
    return replace(
        configuration,
        required_dependencies=(
            *configuration.required_dependencies,
            *provider_dependencies,
        ),
        provider_metadata=ProviderPreflightMetadata(
            provider=provider_request.requested_provider.value,
            backend=backend_label,
            generic_checks=configuration.provider_metadata.generic_checks,
            provider_checks=provider_checks,
            daemon_checks=(
                "managed-lxc-daemon-selected-backend",
            ),
            network_checks=(
                "selected-backend-control-network",
            ),
            resource_expectations=(
                "selected-backend-storage-pool",
                "docker-swarm-profile",
            ),
        ),
    )


def _windows_wsl_bridge_required() -> bool:
    value = os.environ.get(WINDOWS_EXPOSURE_ENVIRONMENT, "").strip().casefold()
    return value not in {"0", "false", "no", "off", "disabled"}


def _platform_init_steps(
    *,
    provider_request: NodeProviderSelectionRequest,
    node_provider_selection: NodeProviderSelectionService,
) -> tuple[AsyncWorkflowStep, ...]:
    node_steps = tuple(
        NodeProviderEnsureNodeStep(node, node_provider_selection, provider_request)
        for node in DEFAULT_LXC_PLATFORM_NODES
    )
    return node_steps


def _cluster_docker_steps(
    lxc_docker_install: LxcDockerInstallService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (LxcDockerInstallStep(lxc_docker_install, DEFAULT_LXC_PLATFORM_NODES),)


def _cluster_swarm_bootstrap_steps(
    lxc_swarm_bootstrap: LxcSwarmBootstrapService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (
        LxcSwarmBootstrapStep(lxc_swarm_bootstrap, DEFAULT_LXC_PLATFORM_NODES),
    )


def _platform_reconcile_steps(
    *,
    provider_request: NodeProviderSelectionRequest,
    node_provider_selection: NodeProviderSelectionService,
) -> tuple[AsyncWorkflowStep, ...]:
    return tuple(
        NodeProviderEnsureNodeStep(node, node_provider_selection, provider_request)
        for node in DEFAULT_LXC_PLATFORM_NODES
    )


def _platform_expose_steps(
    lxc_service_exposure: LxcServiceExposureService,
    socat_manager: SocatManager,
    socat_exposure: PortWslSocatExposure,
    *,
    service_profile: ServiceStackProfile,
    live_consent: LiveConsent | None,
) -> tuple[AsyncWorkflowStep, ...]:
    return (
        LxcServiceExposureStep(lxc_service_exposure),
        _WslSocatExposeStep(
            socat_manager,
            socat_exposure,
            service_profile=ServiceStackProfile(service_profile),
            live_consent=live_consent,
        ),
    )


def _platform_repair_lxc_proxy_drift_steps(
    lxc_proxy_drift_repair: LxcProxyDriftRepairService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (LxcProxyDriftRepairStep(lxc_proxy_drift_repair),)


def _platform_verify_steps(
    post_install_preflight: PreflightService,
    *,
    provider_request: NodeProviderSelectionRequest,
    node_provider_selection: NodeProviderSelectionService,
    lxc_service_exposure: LxcServiceExposureService,
) -> tuple[AsyncWorkflowStep, ...]:
    node_steps = tuple(
        NodeProviderVerifyNodeStep(node, node_provider_selection, provider_request)
        for node in DEFAULT_LXC_PLATFORM_NODES
    )
    return (
        post_install_preflight,
        *node_steps,
        LxcServiceExposureVerifyStep(lxc_service_exposure),
        _portainer_endpoint_verify_step(provider_request),
    )


def _cluster_verify_steps(
    lxc_docker_verify: LxcDockerInstallService,
    lxc_swarm_verify: LxcSwarmBootstrapService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (
        LxcDockerVerifyStep(lxc_docker_verify, DEFAULT_LXC_PLATFORM_NODES),
        LxcSwarmVerifyStep(lxc_swarm_verify, DEFAULT_LXC_PLATFORM_NODES),
    )


def _portainer_endpoint_verify_step(
    provider_request: NodeProviderSelectionRequest,
) -> AsyncWorkflowStep:
    backend = _lxc_backend_for_provider_request(provider_request)
    if backend is None:
        return _BlockedPlatformProviderStep(
            target_id=PortainerEndpointVerifyStep.verification_target_id,
            provider_request=provider_request,
            message="Portainer endpoint verification requires a selected LXC backend.",
            reason=LXC_BACKEND_REQUIRED_REASON,
        )
    return PortainerEndpointVerifyStep(
        EnsurePortainerEndpoint(
            portainer_client=LxcPortainerHttpClient(
                backend=backend,
                username="admin",
                password=_operator_secret_value("TSW_PORTAINER_ADMIN_PASSWORD"),
                stack_request_timeout_seconds=_operator_config_int(
                    PORTAINER_STACK_REQUEST_TIMEOUT_ENVIRONMENT,
                    DEFAULT_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS,
                    minimum=1,
                ),
            ),
            endpoint_name=DEFAULT_PORTAINER_ENDPOINT_NAME,
            max_attempts=1,
            wait_seconds=0,
        )
    )


def _wsl_socat_forwarding_plans(
    service_profile: ServiceStackProfile,
) -> tuple[PortForwardingPlan, ...]:
    return tuple(
        PortForwardingPlan(
            strategy=ForwardingStrategy.WSL2_SOCAT,
            service=requirement.service,
            listen_port=requirement.port,
            target_port=requirement.port,
            remediation=("Start WSL socat forwarding after live consent.",),
        )
        for requirement in default_setup_manifest(
            service_profile=service_profile
        ).required_ports
    )


def _wsl_socat_expose_message(status: VerificationStatus) -> str:
    if status == VerificationStatus.VERIFIED:
        return "WSL port exposure is configured for published service ports."
    return "WSL port exposure failed for one or more published service ports."


def _platform_reset_steps(
    provider_request: NodeProviderSelectionRequest,
    node_provider_selection: NodeProviderSelectionService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (
        NodeProviderResetManagedNodesStep(
            DEFAULT_LXC_PLATFORM_NODES,
            node_provider_selection,
            provider_request,
        ),
    )


def _platform_destroy_steps(
    provider_request: NodeProviderSelectionRequest,
    node_provider_selection: NodeProviderSelectionService,
) -> tuple[AsyncWorkflowStep, ...]:
    return (
        NodeProviderDestroyManagedNodesStep(
            DEFAULT_LXC_PLATFORM_NODES,
            node_provider_selection,
            provider_request,
        ),
    )


async def _platform_init_pre_apply_guard(
    preflight: PreflightService,
    node_provider_selection: NodeProviderSelectionService,
    provider_request: NodeProviderSelectionRequest,
    live_consent: LiveConsent | None,
) -> object:
    preflight_result = await preflight.run(live_consent)
    if not preflight_result.passed:
        return preflight_result
    return await node_provider_selection.verify_provider_selection(provider_request)


def _wsl_lxc_lifecycle_capability_available() -> bool:
    """Compatibility wrapper retaining the legacy composition patch point."""

    return (
        _wsl_unprivileged_userns_clone_available()
        and Path("/sys/fs/cgroup/cgroup.controllers").exists()
        and Path("/proc/self/uid_map").exists()
    )


def _wsl_unprivileged_userns_clone_available(
    path: Path = Path("/proc/sys/kernel/unprivileged_userns_clone"),
) -> bool:
    """Delegate the host probe while preserving legacy test injection."""

    if not path.exists():
        return True
    return _linux_text_file_equals(path, "1")


def _linux_text_file_equals(path: Path, expected: str) -> bool:
    return _probe_linux_text_file_equals(path, expected)


def _lxc_manager_node() -> NodeSpec:
    manager = next(
        (node for node in DEFAULT_LXC_PLATFORM_NODES if node.role == NodeRole.MANAGER),
        None,
    )
    if manager is None:
        raise ValueError("LXC platform node list must include a manager.")
    return manager


def _deployment_stack_environment(
    service_profile: ServiceStackProfile,
) -> dict[str, dict[str, str]]:
    registry_endpoint = _swarm_registry_endpoint()
    environment = {
        "traefik": {
            TRAEFIK_IMAGE_ENVIRONMENT: _operator_config_value(
                TRAEFIK_IMAGE_ENVIRONMENT,
                "traefik:v3.7.4",
            ),
            TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT: _operator_config_value(
                TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
                DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
            ),
            TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT: _operator_config_value(
                TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
                DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
            ),
            TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT: _operator_config_value(
                TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT,
                DEFAULT_TRAEFIK_GUI_USERS_SECRET_NAME,
            ),
        },
        "nexus": {
            NEXUS_IMAGE_ENVIRONMENT: _operator_config_value(
                NEXUS_IMAGE_ENVIRONMENT,
                "sonatype/nexus3:3.75.1",
            ),
        },
        "jenkins": {
            JENKINS_IMAGE_ENVIRONMENT: _operator_config_value(
                JENKINS_IMAGE_ENVIRONMENT,
                f"{registry_endpoint}/jenkins:0.2.0",
            ),
            "TSW_JENKINS_ADMIN_PASSWORD": _operator_secret_value("TSW_JENKINS_ADMIN_PASSWORD"),
        },
        "pulsar": {
            PULSAR_IMAGE_ENVIRONMENT: _operator_config_value(
                PULSAR_IMAGE_ENVIRONMENT,
                DEFAULT_PULSAR_IMAGE,
            ),
            PULSAR_MANAGER_IMAGE_ENVIRONMENT: _operator_config_value(
                PULSAR_MANAGER_IMAGE_ENVIRONMENT,
                DEFAULT_PULSAR_MANAGER_IMAGE,
            ),
            PULSAR_MANAGER_BOOTSTRAP_IMAGE_ENVIRONMENT: _operator_config_value(
                PULSAR_MANAGER_BOOTSTRAP_IMAGE_ENVIRONMENT,
                "python:3.12.13-alpine3.23",
            ),
            "TSW_PULSAR_TOKEN_SECRET_KEY": _operator_secret_value("TSW_PULSAR_TOKEN_SECRET_KEY"),
            "TSW_PULSAR_ADMIN_TOKEN": _operator_secret_value("TSW_PULSAR_ADMIN_TOKEN"),
            "TSW_PULSAR_MANAGER_ADMIN_PASSWORD": _operator_secret_value("TSW_PULSAR_MANAGER_ADMIN_PASSWORD"),
        },
        "sonarqube": {
            "TSW_SONARQUBE_POSTGRES_PASSWORD": _operator_secret_value("TSW_SONARQUBE_POSTGRES_PASSWORD"),
            "TSW_POSTGRES_PASSWORD": _operator_secret_value("TSW_POSTGRES_PASSWORD"),
        }
    }
    if service_profile is not ServiceStackProfile.SERVICE_ACCESS:
        return environment

    _infisical_provider_mode()

    environment["service-access"] = {
        SERVICE_ACCESS_DASHBOARD_IMAGE_ENVIRONMENT: _operator_config_value(
            SERVICE_ACCESS_DASHBOARD_IMAGE_ENVIRONMENT,
            f"{registry_endpoint}/service-access-dashboard:0.2.0",
        ),
        SERVICE_ACCESS_NGINX_IMAGE_ENVIRONMENT: _operator_config_value(
            SERVICE_ACCESS_NGINX_IMAGE_ENVIRONMENT,
            f"{registry_endpoint}/service-access-nginx:0.2.0",
        ),
    }
    environment["infisical"] = {
        INFISICAL_ENCRYPTION_KEY_ENVIRONMENT: _operator_secret_value(
            INFISICAL_ENCRYPTION_KEY_ENVIRONMENT,
        ),
        INFISICAL_AUTH_SECRET_ENVIRONMENT: _operator_secret_value(
            INFISICAL_AUTH_SECRET_ENVIRONMENT,
        ),
        INFISICAL_LOGIN_EMAIL_ENVIRONMENT: _operator_secret_value(
            INFISICAL_LOGIN_EMAIL_ENVIRONMENT,
        ),
        INFISICAL_PASSWORD_ENVIRONMENT: _operator_secret_value(
            INFISICAL_PASSWORD_ENVIRONMENT,
        ),
        INFISICAL_ADMIN_FIRST_NAME_ENVIRONMENT: _operator_config_value(
            INFISICAL_ADMIN_FIRST_NAME_ENVIRONMENT,
            "Tiny",
        ),
        INFISICAL_ADMIN_LAST_NAME_ENVIRONMENT: _operator_config_value(
            INFISICAL_ADMIN_LAST_NAME_ENVIRONMENT,
            "Admin",
        ),
        INFISICAL_POSTGRES_PASSWORD_ENVIRONMENT: _operator_secret_value(
            INFISICAL_POSTGRES_PASSWORD_ENVIRONMENT,
        ),
        INFISICAL_REDIS_PASSWORD_ENVIRONMENT: _operator_secret_value(
            INFISICAL_REDIS_PASSWORD_ENVIRONMENT,
        ),
    }
    _add_optional_config(
        environment["infisical"],
        INFISICAL_IMAGE_ENVIRONMENT,
    )
    _add_optional_config(
        environment["infisical"],
        INFISICAL_POSTGRES_IMAGE_ENVIRONMENT,
    )
    _add_optional_config(
        environment["infisical"],
        INFISICAL_REDIS_IMAGE_ENVIRONMENT,
    )
    return environment



def _infisical_secret_seed_steps(
    service_profile: ServiceStackProfile,
) -> list[EnsureInfisicalSecretItems]:
    if service_profile is not ServiceStackProfile.SERVICE_ACCESS:
        return []
    if os.environ.get(SEED_INFISICAL_ITEMS_ENVIRONMENT) != "1":
        return []
    return [
        EnsureInfisicalSecretItems(
            infisical_client=PlaywrightInfisicalClient(
                base_url=_self_hosted_infisical_url(),
            ),
            login_email=_operator_secret_value(INFISICAL_LOGIN_EMAIL_ENVIRONMENT),
            password=_operator_secret_value(INFISICAL_PASSWORD_ENVIRONMENT),
            items=_infisical_seed_items(),
        ),
    ]


def _infisical_apply_readiness_steps(
    service_profile: ServiceStackProfile,
    *,
    service_stack_by_name: dict[str, ServiceStackContract],
) -> tuple[EndpointReadinessCheck, ...]:
    if service_profile is not ServiceStackProfile.SERVICE_ACCESS:
        readiness_steps: list[EndpointReadinessCheck] = []
        return tuple(readiness_steps)
    attempts = _operator_config_int(
        INFISICAL_READINESS_ATTEMPTS_ENVIRONMENT,
        DEFAULT_INFISICAL_READINESS_ATTEMPTS,
        minimum=1,
    )
    interval = _operator_config_float(
        INFISICAL_READINESS_INTERVAL_ENVIRONMENT,
        DEFAULT_INFISICAL_READINESS_INTERVAL_SECONDS,
        minimum=0,
    )
    readiness_steps = [
        EndpointReadinessCheck(
            service_stack_by_name["infisical"],
            verification_target_id="deployment:infisical-bootstrap-service-readiness",
            max_attempts=attempts,
            wait_seconds=int(interval),
        ),
        EndpointReadinessCheck(
            service_stack_by_name["service-access"],
            verification_target_id="deployment:infisical-bootstrap-access-readiness",
            max_attempts=attempts,
            wait_seconds=int(interval),
        ),
    ]
    return tuple(readiness_steps)


def _infisical_bootstrap_steps(
    service_profile: ServiceStackProfile,
    *,
    cli: InfisicalCliClient | None = None,
    swarm_runtime: LxcSwarmRuntime | None = None,
) -> list[EnsureInfisicalSilentInstall]:
    if service_profile is not ServiceStackProfile.SERVICE_ACCESS:
        return []
    infisical_url = _self_hosted_infisical_url()
    return [
        EnsureInfisicalSilentInstall(
            cli=cli or InfisicalCliClient(base_url=infisical_url),
            storage=LocalFileStorage(),
            bootstrap_client=InfisicalBootstrapHttpClient(
                base_url=infisical_url,
                readiness_attempts=_operator_config_int(
                    INFISICAL_READINESS_ATTEMPTS_ENVIRONMENT,
                    DEFAULT_INFISICAL_READINESS_ATTEMPTS,
                    minimum=1,
                ),
                readiness_interval_seconds=_operator_config_float(
                    INFISICAL_READINESS_INTERVAL_ENVIRONMENT,
                    DEFAULT_INFISICAL_READINESS_INTERVAL_SECONDS,
                    minimum=0,
                ),
                readiness_recovery=(
                    swarm_runtime.recover_infisical_migration_lock
                    if swarm_runtime is not None
                    else None
                ),
            ),
            config=InfisicalSilentInstallConfig(
                external_url=infisical_url,
                internal_url=_operator_config_value(
                    INFISICAL_INTERNAL_URL_ENVIRONMENT,
                    _local_http_url("infisical", "8080"),
                ),
                admin_email=_required_operator_secret_value(
                    INFISICAL_LOGIN_EMAIL_ENVIRONMENT,
                ),
                admin_first_name=_operator_config_value(
                    INFISICAL_ADMIN_FIRST_NAME_ENVIRONMENT,
                    "Tiny",
                ),
                admin_last_name=_operator_config_value(
                    INFISICAL_ADMIN_LAST_NAME_ENVIRONMENT,
                    "Admin",
                ),
                admin_password=_required_operator_secret_value(
                    INFISICAL_PASSWORD_ENVIRONMENT,
                ),
                organization=_operator_config_value(
                    INFISICAL_ORGANIZATION_ENVIRONMENT,
                    DEFAULT_INFISICAL_ORGANIZATION,
                ),
                encryption_key=_required_operator_secret_value(
                    INFISICAL_ENCRYPTION_KEY_ENVIRONMENT,
                ),
                auth_secret=_required_operator_secret_value(
                    INFISICAL_AUTH_SECRET_ENVIRONMENT,
                ),
                postgres_password=_required_operator_secret_value(
                    INFISICAL_POSTGRES_PASSWORD_ENVIRONMENT,
                ),
                redis_password=_operator_secret_value(INFISICAL_REDIS_PASSWORD_ENVIRONMENT),
            ),
        ),
    ]


def _with_infisical_post_apply_steps(
    application_steps: tuple[object, ...],
    post_steps: tuple[object, ...],
) -> tuple[object, ...]:
    if not post_steps:
        return application_steps
    ordered_steps: list[object] = []
    inserted = False
    for step in application_steps:
        ordered_steps.append(step)
        service_stack = getattr(step, "service_stack", None)
        if getattr(service_stack, "stack_name", "") == "service-access":
            ordered_steps.extend(post_steps)
            inserted = True
    if not inserted:
        ordered_steps.extend(post_steps)
    return tuple(ordered_steps)


def _prioritize_infisical_apply_steps(
    application_steps: tuple[object, ...],
) -> tuple[object, ...]:
    priority_stack_names = ("traefik", "infisical", "service-access")
    prioritized: list[object] = []
    remaining = list(application_steps)
    for stack_name in priority_stack_names:
        for index, step in enumerate(remaining):
            service_stack = getattr(step, "service_stack", None)
            if getattr(service_stack, "stack_name", "") == stack_name:
                prioritized.append(step)
                del remaining[index]
                break
    return (*prioritized, *remaining)


def _with_post_stack_steps(
    application_steps: tuple[object, ...],
    stack_name: str,
    post_steps: tuple[object, ...],
) -> tuple[object, ...]:
    if not post_steps:
        return application_steps
    ordered_steps: list[object] = []
    inserted = False
    for step in application_steps:
        ordered_steps.append(step)
        service_stack = getattr(step, "service_stack", None)
        if getattr(service_stack, "stack_name", "") == stack_name:
            ordered_steps.extend(post_steps)
            inserted = True
    if not inserted:
        ordered_steps.extend(post_steps)
    return tuple(ordered_steps)


def _infisical_seed_items() -> tuple[InfisicalSecretItem, ...]:
    return (
        InfisicalSecretItem(
            "platform/jenkins",
            _operator_config_value("TSW_JENKINS_ADMIN_USERNAME", "admin"),
            _required_operator_secret_value("TSW_JENKINS_ADMIN_PASSWORD"),
        ),
        InfisicalSecretItem(
            "platform/nexus",
            _operator_config_value("TSW_NEXUS_ADMIN_USERNAME", "admin"),
            _required_operator_secret_value("TSW_NEXUS_ADMIN_PASSWORD"),
        ),
        InfisicalSecretItem(
            "platform/portainer",
            _operator_config_value("TSW_PORTAINER_USERNAME", "admin"),
            _required_operator_secret_value("TSW_PORTAINER_ADMIN_PASSWORD"),
        ),
        InfisicalSecretItem(
            "platform/pulsar",
            "admin",
            _required_operator_secret_value("TSW_PULSAR_ADMIN_TOKEN"),
        ),
        InfisicalSecretItem(
            "platform/pulsar-manager",
            "admin",
            _required_operator_secret_value("TSW_PULSAR_MANAGER_ADMIN_PASSWORD"),
        ),
        InfisicalSecretItem(
            "platform/sonarqube",
            _operator_config_value("TSW_SONARQUBE_ADMIN_USERNAME", "admin"),
            _required_operator_secret_value("TSW_SONARQUBE_ADMIN_PASSWORD"),
        ),
    )
