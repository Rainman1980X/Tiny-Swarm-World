"""Setup and aggregate application composition boundary.

Concrete setup service construction lives in this focused
infrastructure module. Runtime compatibility symbols are refreshed before
calls so legacy facade patch points remain effective.
"""

from __future__ import annotations

import os
from pathlib import Path

from tiny_swarm_world.application.services.platform.workflow.update import (
    ClassicUpdateWorkflow,
)
from tiny_swarm_world.domain.update import image_override_environment_name
from tiny_swarm_world.infrastructure.adapters.update import JsonUpdateStateStore

from .composition_runtime import (
    AGGREGATE_INSTANCE,
    ApplicationServices,
    ArtifactWorkflowResult,
    ComposeFileRepositoryYaml,
    ConfigurationValidationService,
    DEFAULT_SETUP_SERVICE_PROFILE,
    LiveConsent,
    LocalFileStorage,
    NodeProviderSelectionRequest,
    PortUI,
    PreflightResult,
    STATUS_ERROR,
    ServiceStackProfile,
    SetupServices,
    SetupWorkflow,
    SetupWorkflowPhase,
    SetupWorkflowResult,
    SetupWorkflows,
    StaticArtifactContractPreflight,
    _build_artifact_readiness_gate,
    _build_deployment_services_for_request,
    _build_method_trace_sink,
    _build_platform_services_for_request,
    _build_preflight_service_for_request,
    _build_workflow_progress_sink,
    _new_installation_trace_correlation_id,
    _operator_config_float,
    _operator_config_int,
    _setup_result_status,
    build_artifact_services_for_provider,
    build_host_preparation_service,
    default_installation_plan,
    default_project_paths,
)
from . import composition_runtime as _runtime

_BOUNDARY_FUNCTION_NAMES = frozenset(["run_setup_with_terminal_status","build_setup_services","build_application_services"])
_RUNTIME_SYMBOL_NAMES = frozenset(["AGGREGATE_INSTANCE","ApplicationServices","ArtifactWorkflowResult","ComposeFileRepositoryYaml","ConfigurationValidationService","DEFAULT_SETUP_SERVICE_PROFILE","LiveConsent","LocalFileStorage","NodeProviderSelectionRequest","PortUI","PreflightResult","STATUS_ERROR","ServiceStackProfile","SetupServices","SetupWorkflow","SetupWorkflowPhase","SetupWorkflowResult","SetupWorkflows","StaticArtifactContractPreflight","_build_artifact_readiness_gate","_build_deployment_services_for_request","_build_method_trace_sink","_build_platform_services_for_request","_build_preflight_service_for_request","_build_workflow_progress_sink","_new_installation_trace_correlation_id","_operator_config_float","_operator_config_int","_setup_result_status","build_artifact_services_for_provider","build_host_preparation_service","default_installation_plan","default_project_paths","run_setup_with_terminal_status","build_setup_services","build_application_services"])


def _refresh_runtime_symbols() -> None:
    for name in _RUNTIME_SYMBOL_NAMES:
        if name not in _BOUNDARY_FUNCTION_NAMES:
            globals()[name] = getattr(_runtime, name)


_refresh_runtime_symbols()


async def run_setup_with_terminal_status(
    live_consent: LiveConsent,
    action: str,
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> SetupWorkflowResult:
    if not live_consent.accepted:
        raise ValueError("setup run requires accepted live consent")

    # Resolve the established facade at call time so legacy integrations and
    # tests that patch composition builders continue to observe this boundary.
    from . import composition as facade

    ui = facade.build_setup_ui()
    ui.start_in_thread()
    try:
        services = facade.build_setup_services(
            live_consent,
            service_profile=service_profile,
            node_provider_request=node_provider_request,
            allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
            ui=ui,
            configuration_validation=facade.build_configuration_validation_service(),
        )
        match action:
            case "run":
                result = await services.workflows.run.run()
            case _:
                raise ValueError(f"Unsupported setup workflow action: {action}")
        ui.update_status(
            AGGREGATE_INSTANCE,
            task="setup run",
            step="finished",
            result=_setup_result_status(result),
        )
        return result
    except Exception:
        ui.update_status(
            AGGREGATE_INSTANCE,
            task="setup run",
            step="exception",
            result=STATUS_ERROR,
        )
        raise
    finally:
        if ui.ui_thread is not None:
            await ui.ui_thread

def build_setup_services(
    live_consent: LiveConsent,
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    ui: PortUI | None = None,
    configuration_validation: ConfigurationValidationService | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> SetupServices:
    project_paths = default_project_paths()
    selected_service_profile = ServiceStackProfile(service_profile)
    preflight = _build_preflight_service_for_request(
        selected_service_profile,
        node_provider_request,
        configuration_validation=configuration_validation,
        project_paths=project_paths,
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
    )
    artifact_contract_preflight = StaticArtifactContractPreflight(
        compose_repository=ComposeFileRepositoryYaml(
            project_paths=project_paths,
            service_profile=selected_service_profile,
        ),
        storage=LocalFileStorage(),
    )
    artifact_readiness_gate = _build_artifact_readiness_gate(
        project_paths,
        node_provider_request,
    )
    host_preparation = build_host_preparation_service(live_consent)
    trace_correlation_id = _new_installation_trace_correlation_id()
    workflow_progress = _build_workflow_progress_sink(ui)
    platform = _build_platform_services_for_request(
        service_profile,
        live_consent,
        node_provider_request,
        ui=ui,
        trace_correlation_id=trace_correlation_id,
        allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
    )
    artifacts = build_artifact_services_for_provider(
        node_provider_request=node_provider_request,
        ui=ui,
        progress=workflow_progress,
    )
    deployment = _build_deployment_services_for_request(
        service_profile=service_profile,
        node_provider_request=node_provider_request,
        ui=ui,
        progress=workflow_progress,
    )
    method_trace = _build_method_trace_sink(ui)
    static_preflight_result: PreflightResult | None = None
    artifact_bootstrap_result: ArtifactWorkflowResult | None = None

    def run_artifact_contract_preflight() -> PreflightResult:
        nonlocal static_preflight_result
        static_preflight_result = artifact_contract_preflight.run()
        return static_preflight_result

    async def run_artifact_bootstrap():
        nonlocal artifact_bootstrap_result
        artifact_bootstrap_result = await artifacts.workflows.prepare.run_bootstrap()
        return artifact_bootstrap_result

    def run_artifact_readiness_gate() -> PreflightResult:
        return artifact_readiness_gate.run(
            static_preflight=static_preflight_result,
            artifact_bootstrap=artifact_bootstrap_result,
        )

    def traced_phase(name: str, runner) -> SetupWorkflowPhase:
        return SetupWorkflowPhase(
            name,
            runner,
            method_trace=method_trace,
            trace_correlation_id=trace_correlation_id,
        )

    return SetupServices(
        workflows=SetupWorkflows(
            run=SetupWorkflow(
                (
                    traced_phase("preflight", lambda: preflight.run(live_consent)),
                    traced_phase(
                        "artifact contract preflight",
                        run_artifact_contract_preflight,
                    ),
                    traced_phase("host prepare", host_preparation.prepare),
                    traced_phase("host verify", host_preparation.verify),
                    traced_phase("platform init", lambda: platform.workflows.init.run()),
                    traced_phase(
                        "platform reconcile",
                        lambda: platform.workflows.reconcile.run(),
                    ),
                    traced_phase(
                        "cluster docker",
                        lambda: platform.workflows.cluster.docker.run(),
                    ),
                    traced_phase(
                        "cluster swarm bootstrap",
                        lambda: platform.workflows.cluster.swarm_bootstrap.run(),
                    ),
                    traced_phase(
                        "cluster verify",
                        lambda: platform.workflows.cluster.verify.run(),
                    ),
                    traced_phase(
                        "platform expose",
                        lambda: platform.workflows.expose.run(),
                    ),
                    traced_phase(
                        "deployment bootstrap",
                        lambda: deployment.workflows.bootstrap.run(),
                    ),
                    traced_phase("artifact bootstrap", run_artifact_bootstrap),
                    traced_phase("artifact readiness gate", run_artifact_readiness_gate),
                    traced_phase(
                        "artifacts prepare",
                        lambda: artifacts.workflows.prepare.run_after_bootstrap(
                            artifact_bootstrap_result
                        ),
                    ),
                    traced_phase(
                        "artifacts verify",
                        lambda: artifacts.workflows.verify.run(),
                    ),
                    traced_phase(
                        "deployment apply",
                        lambda: deployment.workflows.apply.run(),
                    ),
                    traced_phase(
                        "deployment verify",
                        lambda: deployment.workflows.verify.run(),
                    ),
                    traced_phase("platform verify", lambda: platform.workflows.verify.run()),
                ),
                live_consent=live_consent,
                progress=workflow_progress,
                method_trace=method_trace,
                trace_correlation_id=trace_correlation_id,
                installation_plan=default_installation_plan(),
                timeout_seconds=_operator_config_float(
                    "TSW_SETUP_WORKFLOW_TIMEOUT_SECONDS",
                    3600.0,
                    minimum=1.0,
                ),
                heartbeat_interval_seconds=_operator_config_float(
                    "TSW_SETUP_HEARTBEAT_INTERVAL_SECONDS",
                    30.0,
                    minimum=1.0,
                ),
                max_concurrency=_operator_config_int(
                    "TSW_SETUP_MAX_CONCURRENCY",
                    2,
                    minimum=1,
                ),
            )
        )
    )


def build_classic_update_workflow(
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
) -> ClassicUpdateWorkflow:
    from . import composition as facade

    compose_repository = facade.build_compose_file_repository(
        service_profile=service_profile,
    )

    def deployment_workflow_for(plan):
        image_environment = image_override_environment_name(
            plan.stack_name,
            plan.service_name,
        )
        services = facade.build_deployment_services_for_provider(
            service_profile=service_profile,
            node_provider_request=node_provider_request,
            image_overrides={image_environment: plan.target_image},
            update_stack_name=plan.stack_name,
        )
        return services.workflows.apply

    configured_state_root = os.environ.get("TSW_UPDATE_STATE_ROOT", "").strip()
    if configured_state_root:
        state_root = Path(configured_state_root).expanduser()
    else:
        state_home = os.environ.get("XDG_STATE_HOME", "").strip()
        state_root = (
            Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
        ) / "tiny-swarm-world" / "updates"
    return ClassicUpdateWorkflow(
        compose_repository=compose_repository,
        deployment_workflow_factory=deployment_workflow_for,
        state_store=JsonUpdateStateStore(state_root),
    )

def build_application_services(
    live_consent: LiveConsent | None = None,
    service_profile: ServiceStackProfile | str = DEFAULT_SETUP_SERVICE_PROFILE,
    node_provider_request: NodeProviderSelectionRequest | None = None,
    ui: PortUI | None = None,
    allow_wsl_windows_filesystem: bool = False,
) -> ApplicationServices:
    return ApplicationServices(
        platform=_build_platform_services_for_request(
            service_profile,
            live_consent,
            node_provider_request,
            ui=ui,
            allow_wsl_windows_filesystem=allow_wsl_windows_filesystem,
        ),
        artifacts=build_artifact_services_for_provider(
            node_provider_request=node_provider_request
        ),
        deployment=_build_deployment_services_for_request(
            service_profile=service_profile,
            node_provider_request=node_provider_request,
            ui=ui,
        ),
    )


_BOUNDARY_DEFAULTS = {
    name: globals()[name]
    for name in _BOUNDARY_FUNCTION_NAMES
}
