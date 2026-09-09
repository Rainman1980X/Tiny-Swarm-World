"""Deployment composition boundary.

Concrete deployment service construction lives in this focused
infrastructure module. Runtime compatibility symbols are refreshed before
calls so legacy facade patch points remain effective.
"""

from __future__ import annotations

from tiny_swarm_world.application.services.deployment.ensure_external_swarm_secret import (
    EnsureExternalSwarmSecret,
)
from tiny_swarm_world.application.services.deployment.verify_external_swarm_input import (
    VerifyExternalSwarmInput,
)
from tiny_swarm_world.domain.configuration.configuration_contract import (
    validate_traefik_htpasswd,
)

from .composition_configuration import TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT
from .composition_runtime import (
    ComposeFileRepositoryYaml,
    DEFAULT_DEPLOYMENT_VERIFY_TIMEOUT_SECONDS,
    DEFAULT_PORTAINER_ENDPOINT_NAME,
    DEFAULT_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_SETUP_SERVICE_PROFILE,
    DEFAULT_TRAEFIK_GUI_USERS_SECRET_NAME,
    DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
    DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
    DEPLOYMENT_VERIFY_TIMEOUT_ENVIRONMENT,
    DeploymentApplyStep,
    DeploymentApplyWorkflow,
    DeploymentPreApplyStep,
    DeploymentServices,
    DeploymentVerifyWorkflow,
    DeploymentWorkflowKind,
    DeploymentWorkflows,
    EndpointReadinessCheck,
    EnsureNexusAdminAccess,
    EnsurePortainerAdminAccess,
    EnsurePortainerEndpoint,
    EnsureSonarqubeAdminAccess,
    EnsureSwarmStack,
    InfisicalCliClient,
    InfisicalSecretSyncStep,
    LXC_BACKEND_REQUIRED_REASON,
    LocalFileStorage,
    LxcPortainerAdminClient,
    LxcPortainerHttpClient,
    LxcSwarmRuntime,
    ManagedLxcBackend,
    NodeProviderSelectionRequest,
    PORTAINER_STACK_REQUEST_TIMEOUT_ENVIRONMENT,
    PortUI,
    PortWorkflowProgress,
    RoutingEvidenceLocalRepository,
    SecretConsumptionVerifier,
    SecretDiscoveryStep,
    SecretEvidenceWriter,
    SecretManifestRenderer,
    ServiceStackProfile,
    SonarqubeHttpClient,
    TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT,
    TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
    TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
    WriteEffectiveAccessModelEvidence,
    _BlockedDeploymentWorkflow,
    _LXC_SUPPORTED_BACKENDS,
    _PrepareLxcStackAssets,
    _default_node_provider_request,
    _deployment_stack_environment,
    _infisical_apply_readiness_steps,
    _infisical_bootstrap_steps,
    _infisical_secret_seed_steps,
    _local_http_url,
    _lxc_backend_for_provider_request,
    _operator_config_float,
    _operator_config_int,
    _operator_config_value,
    _operator_secret_value,
    _prioritize_infisical_apply_steps,
    _self_hosted_infisical_url,
    _with_infisical_post_apply_steps,
    _with_post_stack_steps,
    backend_cli,
    build_process_runner,
    cast,
    default_project_paths,
    os,
    service_stack_contracts_for_profile,
    shutil,
)
from . import composition_runtime as _runtime

_BOUNDARY_FUNCTION_NAMES = frozenset(["build_deployment_services_for_provider","build_lxc_deployment_services"])
_TRAEFIK_GUI_USERS_EXTERNAL_SECRET_TARGET = "deployment:traefik-gui-input"
_RUNTIME_SYMBOL_NAMES = frozenset(["ComposeFileRepositoryYaml","DEFAULT_DEPLOYMENT_VERIFY_TIMEOUT_SECONDS","DEFAULT_PORTAINER_ENDPOINT_NAME","DEFAULT_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS","DEFAULT_SETUP_SERVICE_PROFILE","DEFAULT_TRAEFIK_GUI_USERS_SECRET_NAME","DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME","DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME","DEPLOYMENT_VERIFY_TIMEOUT_ENVIRONMENT","DeploymentApplyStep","DeploymentApplyWorkflow","DeploymentPreApplyStep","DeploymentServices","DeploymentVerifyWorkflow","DeploymentWorkflowKind","DeploymentWorkflows","EndpointReadinessCheck","EnsureNexusAdminAccess","EnsurePortainerAdminAccess","EnsurePortainerEndpoint","EnsureSonarqubeAdminAccess","EnsureSwarmStack","InfisicalCliClient","InfisicalSecretSyncStep","LXC_BACKEND_REQUIRED_REASON","LocalFileStorage","LxcPortainerAdminClient","LxcPortainerHttpClient","LxcSwarmRuntime","ManagedLxcBackend","NodeProviderSelectionRequest","PORTAINER_STACK_REQUEST_TIMEOUT_ENVIRONMENT","PortUI","PortWorkflowProgress","RoutingEvidenceLocalRepository","SecretConsumptionVerifier","SecretDiscoveryStep","SecretEvidenceWriter","SecretManifestRenderer","ServiceStackProfile","SonarqubeHttpClient","TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT","TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT","TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT","WriteEffectiveAccessModelEvidence","_BlockedDeploymentWorkflow","_LXC_SUPPORTED_BACKENDS","_PrepareLxcStackAssets","_default_node_provider_request","_deployment_stack_environment","_infisical_apply_readiness_steps","_infisical_bootstrap_steps","_infisical_secret_seed_steps","_local_http_url","_lxc_backend_for_provider_request","_operator_config_float","_operator_config_int","_operator_config_value","_operator_secret_value","_prioritize_infisical_apply_steps","_self_hosted_infisical_url","_with_infisical_post_apply_steps","_with_post_stack_steps","backend_cli","build_process_runner","cast","default_project_paths","os","service_stack_contracts_for_profile","shutil","build_deployment_services_for_provider","build_lxc_deployment_services"])


def _refresh_runtime_symbols() -> None:
    for name in _RUNTIME_SYMBOL_NAMES:
        if name not in _BOUNDARY_FUNCTION_NAMES:
            globals()[name] = getattr(_runtime, name)


_refresh_runtime_symbols()


def build_deployment_services_for_provider(
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    ui: PortUI | None = None,
    progress: PortWorkflowProgress | None = None,
) -> DeploymentServices:
    provider_request = node_provider_request or _default_node_provider_request()
    backend = _lxc_backend_for_provider_request(provider_request)
    backend_executable = None if backend is None else backend_cli(backend)
    if backend is not None and backend in _LXC_SUPPORTED_BACKENDS and backend_executable is not None and shutil.which(backend_executable):
        return build_lxc_deployment_services(
            service_profile=service_profile,
            backend=backend,
            ui=ui,
            progress=progress,
        )
    return DeploymentServices(
        workflows=DeploymentWorkflows(
            bootstrap=cast(
                DeploymentApplyWorkflow,
                _BlockedDeploymentWorkflow(
                    DeploymentWorkflowKind.BOOTSTRAP,
                    LXC_BACKEND_REQUIRED_REASON,
                ),
            ),
            apply=cast(
                DeploymentApplyWorkflow,
                _BlockedDeploymentWorkflow(
                    DeploymentWorkflowKind.APPLY,
                    LXC_BACKEND_REQUIRED_REASON,
                ),
            ),
            verify=cast(
                DeploymentVerifyWorkflow,
                _BlockedDeploymentWorkflow(
                    DeploymentWorkflowKind.VERIFY,
                    LXC_BACKEND_REQUIRED_REASON,
                ),
            ),
        )
    )
def build_lxc_deployment_services(
    *,
    backend: ManagedLxcBackend,
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    ui: PortUI | None = None,
    progress: PortWorkflowProgress | None = None,
) -> DeploymentServices:
    project_paths = default_project_paths()
    local_file_storage = LocalFileStorage()
    selected_service_profile = ServiceStackProfile(service_profile)
    service_stack_contracts = service_stack_contracts_for_profile(selected_service_profile)
    compose_repository = ComposeFileRepositoryYaml(
        project_paths=project_paths,
        service_profile=selected_service_profile,
    )
    routing_evidence_step = WriteEffectiveAccessModelEvidence(
        effective_access_model_repository=compose_repository,
        routing_evidence_repository=RoutingEvidenceLocalRepository(
            project_paths=project_paths,
        ),
        service_profile=selected_service_profile,
    )
    traefik_tls_cert_secret_name = _operator_config_value(
        TRAEFIK_TLS_CERT_SECRET_NAME_ENVIRONMENT,
        DEFAULT_TRAEFIK_TLS_CERT_SECRET_NAME,
    )
    traefik_tls_key_secret_name = _operator_config_value(
        TRAEFIK_TLS_KEY_SECRET_NAME_ENVIRONMENT,
        DEFAULT_TRAEFIK_TLS_KEY_SECRET_NAME,
    )
    from tiny_swarm_world.infrastructure.adapters.ingress.local_tls_contract_resolver import (
        LocalTlsContractResolver,
    )
    from tiny_swarm_world.infrastructure.adapters.ingress.tls_state import (
        canonical_tls_state_root,
    )

    swarm_runtime = LxcSwarmRuntime(
        backend=backend,
        process_runner=build_process_runner(),
        project_paths=project_paths,
        service_access_dashboard_renderer=compose_repository.render_service_access_dashboard,
        portainer_admin_password=_operator_secret_value("TSW_PORTAINER_ADMIN_PASSWORD"),
        traefik_tls_cert_secret_name=traefik_tls_cert_secret_name,
        traefik_tls_key_secret_name=traefik_tls_key_secret_name,
        tls_contract_resolver=LocalTlsContractResolver(
            state_root=canonical_tls_state_root(),
            certificate_secret_name=traefik_tls_cert_secret_name,
            private_key_secret_name=traefik_tls_key_secret_name,
        ),
    )
    stack_environment = _deployment_stack_environment(selected_service_profile)
    secret_manifest_entries = SecretManifestRenderer(local_file_storage).run()
    portainer_admin_client = LxcPortainerAdminClient(backend=backend)
    portainer_client = LxcPortainerHttpClient(
        backend=backend,
        username="admin",
        password=_operator_secret_value("TSW_PORTAINER_ADMIN_PASSWORD"),
        stack_request_timeout_seconds=_operator_config_int(
            PORTAINER_STACK_REQUEST_TIMEOUT_ENVIRONMENT,
            DEFAULT_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS,
            minimum=1,
        ),
    )
    stack_steps = {
        contract.stack_name: EnsureSwarmStack(
            compose_repository=compose_repository,
            swarm_runtime=swarm_runtime,
            service_stack=contract,
            stack_environment=stack_environment.get(contract.stack_name),
        )
        for contract in service_stack_contracts
    }
    bootstrap_steps = (
        stack_steps["portainer"],
        EnsurePortainerAdminAccess(
            portainer_admin_client=portainer_admin_client,
            username="admin",
            password=_operator_secret_value("TSW_PORTAINER_ADMIN_PASSWORD"),
            max_attempts=60,
            wait_seconds=5,
            ui=ui,
        ),
        EnsurePortainerEndpoint(
            portainer_client=portainer_client,
            endpoint_name=DEFAULT_PORTAINER_ENDPOINT_NAME,
        ),
        stack_steps["nexus"],
    )
    application_steps: tuple[object, ...] = tuple(
        stack_steps[contract.stack_name]
        for contract in service_stack_contracts
        if contract.stack_name not in {"portainer", "nexus", "traefik"}
    )
    if selected_service_profile is ServiceStackProfile.SERVICE_ACCESS:
        application_steps = _prioritize_infisical_apply_steps(
            (stack_steps["traefik"], *application_steps)
        )
    sonarqube_admin_step = EnsureSonarqubeAdminAccess(
        sonarqube_client=SonarqubeHttpClient(
            _operator_config_value(
                "TSW_SONARQUBE_URL",
                _local_http_url("localhost", "12000"),
            )
        ),
        username=_operator_config_value("TSW_SONARQUBE_ADMIN_USERNAME", "admin"),
        password=_operator_secret_value("TSW_SONARQUBE_ADMIN_PASSWORD"),
        progress=progress,
    )
    application_steps = _with_post_stack_steps(
        application_steps,
        "sonarqube",
        (sonarqube_admin_step,),
    )
    service_stack_by_name = {contract.stack_name: contract for contract in service_stack_contracts}
    infisical_apply_readiness_steps = _infisical_apply_readiness_steps(
        selected_service_profile,
        service_stack_by_name=service_stack_by_name,
    )
    infisical_secret_management_steps: tuple[object, ...] = ()
    infisical_seed_steps: tuple[object, ...] = ()
    if selected_service_profile is ServiceStackProfile.SERVICE_ACCESS:
        infisical_cli_client = InfisicalCliClient(base_url=_self_hosted_infisical_url())
        infisical_bootstrap_steps = _infisical_bootstrap_steps(
            selected_service_profile,
            cli=infisical_cli_client,
            swarm_runtime=swarm_runtime,
        )
        secret_discovery_step = SecretDiscoveryStep(
            storage=local_file_storage,
            manifest_entries=secret_manifest_entries,
        )
        infisical_secret_sync_step = InfisicalSecretSyncStep(
            cli=infisical_cli_client,
            storage=local_file_storage,
            manifest_entries=secret_manifest_entries,
            process_environment=os.environ,
        )
        secret_consumption_step = SecretConsumptionVerifier(
            manifest_entries=secret_manifest_entries,
            stack_environment=stack_environment,
            non_stack_consumer_refs={
                "TSW_NEXUS_ADMIN_PASSWORD": EnsureNexusAdminAccess.verification_target_id,
                "TSW_PORTAINER_ADMIN_PASSWORD": EnsurePortainerAdminAccess.verification_target_id,
                "TSW_SONARQUBE_ADMIN_PASSWORD": EnsureSonarqubeAdminAccess.verification_target_id,
            },
        )
        secret_evidence_step = SecretEvidenceWriter(
            storage=local_file_storage,
            discovery=secret_discovery_step,
            sync=infisical_secret_sync_step,
            consumption=secret_consumption_step,
        )
        infisical_secret_management_steps = (
            secret_discovery_step,
            *infisical_bootstrap_steps,
            infisical_secret_sync_step,
            secret_consumption_step,
            secret_evidence_step,
        )
        infisical_seed_steps = tuple(
            _infisical_secret_seed_steps(selected_service_profile)
        )
    readiness_checks = tuple(
        EndpointReadinessCheck(
            service_stack=contract,
            max_attempts=60,
            wait_seconds=5,
        )
        for contract in service_stack_contracts
    )
    pre_apply_steps: list[DeploymentPreApplyStep] = [
        routing_evidence_step,
        _PrepareLxcStackAssets(swarm_runtime, "traefik"),
        _PrepareLxcStackAssets(swarm_runtime, "swagger"),
    ]
    pre_apply_checks: tuple[VerifyExternalSwarmInput, ...] = ()
    if "traefik" in service_stack_by_name:
        traefik_gui_users_secret_name = _operator_config_value(
            TRAEFIK_GUI_USERS_SECRET_NAME_ENVIRONMENT,
            DEFAULT_TRAEFIK_GUI_USERS_SECRET_NAME,
        )
        traefik_gui_users_htpasswd = os.environ.get(
            TRAEFIK_GUI_USERS_HTPASSWD_ENVIRONMENT,
            "",
        ).strip()
        if traefik_gui_users_htpasswd:
            validate_traefik_htpasswd(traefik_gui_users_htpasswd)
            pre_apply_steps.insert(
                0,
                EnsureExternalSwarmSecret(
                    swarm_runtime,
                    traefik_gui_users_secret_name,
                    traefik_gui_users_htpasswd,
                    verification_target_id=_TRAEFIK_GUI_USERS_EXTERNAL_SECRET_TARGET,
                ),
            )
        pre_apply_checks = (
            VerifyExternalSwarmInput(
                swarm_runtime,
                traefik_gui_users_secret_name,
                source_ref="operator_env",
                verification_target_id=_TRAEFIK_GUI_USERS_EXTERNAL_SECRET_TARGET,
            ),
        )
    if selected_service_profile is ServiceStackProfile.SERVICE_ACCESS:
        pre_apply_steps.append(_PrepareLxcStackAssets(swarm_runtime, "service-access"))

    return DeploymentServices(
        workflows=DeploymentWorkflows(
            bootstrap=DeploymentApplyWorkflow(
                bootstrap_steps,
                kind=DeploymentWorkflowKind.BOOTSTRAP,
            ),
            apply=DeploymentApplyWorkflow(
                cast(
                    tuple[DeploymentApplyStep, ...],
                    _with_infisical_post_apply_steps(
                        application_steps,
                        (
                            *infisical_apply_readiness_steps,
                            *infisical_secret_management_steps,
                            *infisical_seed_steps,
                        ),
                    ),
                ),
                pre_apply_steps=tuple(pre_apply_steps),
                pre_apply_checks=pre_apply_checks,
            ),
            verify=DeploymentVerifyWorkflow(
                readiness_checks,
                timeout_seconds=_operator_config_float(
                    DEPLOYMENT_VERIFY_TIMEOUT_ENVIRONMENT,
                    DEFAULT_DEPLOYMENT_VERIFY_TIMEOUT_SECONDS,
                    minimum=1.0,
                ),
            ),
        )
    )


_BOUNDARY_DEFAULTS = {
    name: globals()[name]
    for name in _BOUNDARY_FUNCTION_NAMES
}
