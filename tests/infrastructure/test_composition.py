import asyncio
import os
import unittest
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest.mock import AsyncMock, Mock, patch
from tests.support.async_helpers import async_checkpoint
from tests.support.sonar_safe_literals import ipv4_address, sample_http_url, sample_text

from tiny_swarm_world.application.services.deployment.ensure_swarm_stack import (
    EnsureSwarmStack,
)
from tiny_swarm_world.application.ports.ui.port_ui import (
    AGGREGATE_INSTANCE,
    STATUS_ERROR,
    STATUS_SUCCESS,
    PortUI,
)
from tiny_swarm_world.application.services.platform import PlatformWorkflowStatus
from tiny_swarm_world.application.services.platform.preflight_service import (
    PreflightService,
)
from tiny_swarm_world.application.services.setup import (
    SetupWorkflowKind,
    SetupWorkflowResult,
    SetupWorkflowStatus,
)
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus
from tiny_swarm_world.domain.deployment import (
    ServiceEndpoint,
    ServiceStackContract,
    ServiceStackProfile,
)
from tiny_swarm_world.domain.network import PortRegistry
from tiny_swarm_world.domain.preflight import (
    LIVE_CONSENT_ENVIRONMENT_VALUE,
    LIVE_CONSENT_PHRASE,
    LiveConsent,
)
import tiny_swarm_world.infrastructure.composition as composition
from tiny_swarm_world.infrastructure.adapters.host import (
    LinuxHostSignalReader,
    WslHostSignalReader,
)
from tiny_swarm_world.infrastructure.adapters.preflight import HostPreflightProbe
from tiny_swarm_world.infrastructure.adapters.network import wsl_socat_exposure


def _required_infisical_bootstrap_env() -> dict[str, str]:
    return {
        "TSW_INFISICAL_LOGIN_EMAIL": "admin@example.com",
        "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD": sample_text("master", "-value"),
        "TSW_INFISICAL_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
        "TSW_INFISICAL_AUTH_SECRET": sample_text("auth", "-secret"),
        "TSW_INFISICAL_POSTGRES_PASSWORD": sample_text("pg", "-secret"),
        "TSW_INFISICAL_REDIS_PASSWORD": sample_text("redis", "-secret"),
        "TSW_PORTAINER_ADMIN_PASSWORD": sample_text("portainer", "-value"),
        "TSW_JENKINS_ADMIN_PASSWORD": sample_text("jenkins", "-value"),
        "TSW_PULSAR_TOKEN_SECRET_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        "TSW_PULSAR_ADMIN_TOKEN": "header.payload.signature",
        "TSW_PULSAR_MANAGER_ADMIN_PASSWORD": sample_text("pulsar-manager", "-value"),
        "TSW_POSTGRES_PASSWORD": sample_text("postgres", "-value"),
        "TSW_SONARQUBE_POSTGRES_PASSWORD": sample_text("sonar-pg", "-value"),
        "TSW_SONARQUBE_ADMIN_PASSWORD": sample_text("sonar-admin", "-value!"),
    }


class TestComposition(unittest.TestCase):
    def test_update_builder_wires_observer_without_running_commands_for_preview(self):
        from tiny_swarm_world.domain.deployment import ComposeServiceDefinition
        from tiny_swarm_world.domain.update import ClassicUpdatePlan
        from tiny_swarm_world.infrastructure.adapters.update.lxc_runtime_observer import LxcUpdateRuntimeObserver

        runner = Mock()
        repository = Mock()
        repository.get_services_of.return_value = (
            ComposeServiceDefinition(name="jenkins", image_ref="old:1"),
        )
        request = composition.NodeProviderSelectionRequest(
            requested_provider=composition.NodeProviderKind.LXC_NATIVE,
            preferred_backend=composition.ManagedLxcBackend.INCUS,
        )
        with patch.object(composition, "build_process_runner", return_value=runner), patch.object(
            composition, "build_compose_file_repository", return_value=repository,
        ), patch.object(composition, "build_deployment_services_for_provider") as deployment_builder:
            workflow = composition.build_classic_update_workflow(node_provider_request=request)
            result = asyncio.run(workflow.run(
                ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1"), preview=True, live_consent=None,
            ))
        self.assertIsInstance(workflow.runtime_observer, LxcUpdateRuntimeObserver)
        self.assertIs(workflow.runtime_observer.gateway.process_runner, runner)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(result.executed)
        runner.run_text.assert_not_called()
        deployment_builder.assert_not_called()

    def test_image_update_does_not_bootstrap_or_synchronize_unrelated_secrets(self):
        with (
            patch.object(composition, "ComposeFileRepositoryYaml"),
            patch.object(composition, "LxcSwarmRuntime"),
            patch.object(
                composition, "InfisicalCliClient",
                side_effect=AssertionError("Image updates must not initialize Infisical"),
            ),
        ):
            services = composition.build_lxc_deployment_services(
                backend=composition.ManagedLxcBackend.INCUS,
                service_profile=ServiceStackProfile.SERVICE_ACCESS,
                update_stack_name="jenkins",
            )

        self.assertEqual((), services.workflows.bootstrap.steps)
        self.assertEqual(1, len(services.workflows.apply.steps))
        step = services.workflows.apply.steps[0]
        self.assertIsInstance(step, EnsureSwarmStack)
        self.assertEqual("jenkins", step.service_stack.stack_name)

    def setUp(self):
        self._infisical_env_patcher = patch.dict(
            os.environ,
            _required_infisical_bootstrap_env(),
        )
        self._infisical_env_patcher.start()
        self.addCleanup(self._infisical_env_patcher.stop)

    def test_application_services_separates_service_bundles(self):
        self.assertIsNot(composition.ApplicationServices, composition.PlatformServices)

        field_names = {field.name for field in fields(composition.ApplicationServices)}

        self.assertEqual({"platform", "artifacts", "deployment"}, field_names)

    def test_service_bundle_types_are_distinct_dataclasses(self):
        self.assertNotEqual(composition.PlatformServices, composition.ArtifactServices)
        self.assertNotEqual(
            composition.PlatformServices, composition.DeploymentServices
        )
        self.assertNotEqual(
            composition.ArtifactServices, composition.DeploymentServices
        )

    def test_build_application_services_aggregates_separate_builders(self):
        platform = object()
        artifacts = object()
        deployment = object()

        with patch.object(
            composition,
            "build_platform_services",
            return_value=platform,
        ) as build_platform_services:
            with patch.object(
                composition,
                "build_artifact_services_for_provider",
                return_value=artifacts,
            ) as build_artifact_services:
                with patch.object(
                    composition,
                    "build_deployment_services_for_provider",
                    return_value=deployment,
                ) as build_deployment_services:
                    services = composition.build_application_services()

        self.assertIs(services.platform, platform)
        self.assertIs(services.artifacts, artifacts)
        self.assertIs(services.deployment, deployment)
        build_platform_services.assert_called_once_with(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
            live_consent=None,
            allow_wsl_windows_filesystem=False,
        )
        build_artifact_services.assert_called_once_with(node_provider_request=None)
        build_deployment_services.assert_called_once_with(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
            node_provider_request=None,
        )

    def test_endpoint_readiness_treats_authenticated_http_response_as_reachable(self):
        contract = ServiceStackContract(
            "pulsar",
            ("pulsar",),
            endpoints=(ServiceEndpoint("pulsar-admin-api", "http://localhost:14080"),),
        )
        check = composition.EndpointReadinessCheck(
            contract,
            max_attempts=1,
            wait_seconds=0,
            session=_FakeEndpointSession((401,)),
        )

        verification = check.verify()

        self.assertEqual(VerificationStatus.VERIFIED, verification.status)
        self.assertEqual(
            verification.evidence["endpoint_statuses"], "pulsar-admin-api=http_401"
        )

    def test_endpoint_readiness_does_not_follow_https_redirects(self):
        endpoint_url = "http://localhost"
        session = _FakeEndpointSession((301,))
        contract = ServiceStackContract(
            "traefik",
            ("traefik",),
            endpoints=(ServiceEndpoint("traefik", endpoint_url),),
        )
        check = composition.EndpointReadinessCheck(
            contract,
            max_attempts=1,
            wait_seconds=0,
            session=session,
        )

        verification = check.verify()

        self.assertEqual(VerificationStatus.VERIFIED, verification.status)
        self.assertEqual(verification.evidence["endpoint_statuses"], "traefik=http_301")
        self.assertEqual(session.requests, [(endpoint_url, 5, False)])

    def test_endpoint_readiness_fails_after_connection_errors(self):
        contract = ServiceStackContract(
            "pulsar",
            ("pulsar",),
            endpoints=(ServiceEndpoint("pulsar-admin-api", "http://localhost:14080"),),
        )
        check = composition.EndpointReadinessCheck(
            contract,
            max_attempts=1,
            wait_seconds=0,
            session=_FakeEndpointSession((composition.requests.ConnectionError(),)),
        )

        verification = check.verify()

        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, verification.status)
        self.assertEqual(
            verification.evidence["endpoint_statuses"],
            "pulsar-admin-api=connection_error",
        )

    def test_platform_services_contains_preflight_service(self):
        field_names = {field.name for field in fields(composition.PlatformServices)}

        self.assertIn("preflight", field_names)
        self.assertIn("lxc_node_provider", field_names)
        self.assertIn("node_provider_selection", field_names)
        self.assertIn("lxc_docker_install", field_names)
        self.assertIn("lxc_proxy_drift_repair", field_names)
        self.assertIn("lxc_service_exposure", field_names)
        self.assertIn("lxc_swarm_bootstrap", field_names)

    def test_platform_services_contains_workflow_bundle(self):
        platform_field_names = {
            field.name for field in fields(composition.PlatformServices)
        }
        workflow_field_names = {
            field.name for field in fields(composition.PlatformWorkflows)
        }

        self.assertIn("workflows", platform_field_names)
        self.assertEqual(
            workflow_field_names,
            {
                "init",
                "reconcile",
                "expose",
                "repair_lxc_proxy_drift",
                "reset",
                "destroy",
                "verify",
                "cluster",
            },
        )

    def test_build_preflight_service_loads_port_registry(self):
        registry = PortRegistry(ranges=(), mappings=())
        provider_request = composition.NodeProviderSelectionRequest(
            requested_provider=composition.NodeProviderKind.UNSUPPORTED,
            backend_candidates=(),
        )

        with patch.object(
            composition, "PortRegistryYamlRepository"
        ) as repository_class:
            repository_class.return_value.load.return_value = registry

            service = composition.build_preflight_service(
                node_provider_request=provider_request,
                allow_wsl_windows_filesystem=True,
            )

        self.assertIs(registry, service.port_registry)
        self.assertEqual(repository_class.call_count, 1)
        self.assertIn("project_paths", repository_class.call_args.kwargs)
        repository_class.return_value.load.assert_called_once_with()
        self.assertIsInstance(
            service.host_probe.host_environment_detector,
            composition.HostEnvironmentDetector,
        )
        self.assertIsInstance(
            service.project_filesystem_evaluator,
            composition.EvaluateProjectFilesystem,
        )
        self.assertIsInstance(
            service.project_filesystem_authorizer,
            composition.AuthorizeProjectFilesystem,
        )
        self.assertTrue(service.allow_wsl_windows_filesystem)
        self.assertEqual(
            composition.default_project_paths().repository_root.as_posix(),
            service.project_path,
        )

    def test_build_preflight_service_wires_resource_inspection_and_evidence(self):
        service = composition.build_preflight_service()

        self.assertIsInstance(
            service.resource_inspector, composition.WslResourceInspector
        )
        self.assertIsInstance(
            service.evidence_writer, composition.PreflightEvidenceWriter
        )

    def test_build_hang_diagnostics_reads_bounded_operator_timeout(self):
        with patch.dict(os.environ, {"TSW_HANG_DIAGNOSTICS_TIMEOUT_SECONDS": "3"}):
            diagnostics = composition.build_read_only_hang_diagnostics()

        self.assertEqual(3.0, diagnostics.timeout_seconds)

    def test_preflight_profile_uses_central_resource_thresholds(self):
        configuration = composition._preflight_configuration_for_provider(
            ServiceStackProfile.SERVICE_ACCESS,
            None,
        )

        self.assertEqual(8, configuration.resources.minimum_cpu_count)
        self.assertEqual(16 * 1024**3, configuration.resources.minimum_memory_bytes)

    def test_relative_xdg_state_home_does_not_block_preflight_construction(self):
        with patch.dict(os.environ, {"XDG_STATE_HOME": "relative/state"}, clear=False):
            service = composition.build_preflight_service()

        self.assertIsInstance(
            service.project_filesystem_authorizer,
            composition.AuthorizeProjectFilesystem,
        )

    def test_build_host_environment_detector_has_no_constructor_io(self):
        with (
            patch(
                "pathlib.Path.read_text",
                side_effect=AssertionError("constructor must not read host files"),
            ),
            patch(
                "subprocess.run",
                side_effect=AssertionError("constructor must not run commands"),
            ),
        ):
            detector = composition.build_host_environment_detector()

        self.assertIsInstance(detector, composition.HostEnvironmentDetector)
        self.assertIsInstance(
            detector.linux_signal_reader,
            LinuxHostSignalReader,
        )
        self.assertIsInstance(
            detector.wsl_signal_reader,
            WslHostSignalReader,
        )

    def test_build_host_detection_service_uses_supplied_detector_port(self):
        detector = composition.build_host_environment_detector()

        service = composition.build_host_detection_service(detector)

        self.assertIsInstance(service, composition.DetectHostEnvironment)
        self.assertIs(detector, service.detector)

    def test_windows_wsl_bridge_required_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(composition._windows_wsl_bridge_required())

    def test_windows_wsl_bridge_can_be_disabled_by_operator_environment(self):
        with patch.dict(os.environ, {"TSW_WINDOWS_EXPOSURE": "disabled"}, clear=True):
            self.assertFalse(composition._windows_wsl_bridge_required())

    def test_build_configuration_validation_service_uses_env_file_and_process_environment(
        self,
    ):
        with TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "operator.env"
            env_file.write_text(
                "\n".join(
                    (
                        "TSW_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS=0",
                        "TSW_NEXUS_ADMIN_PASSWORD='file-secret'",
                        "TSW_SONARQUBE_ADMIN_PASSWORD='file-secret'",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            environment = {
                **_required_infisical_bootstrap_env(),
                "TSW_NEXUS_ADMIN_PASSWORD": sample_text("nexus", "-value"),
                "TSW_SONARQUBE_ADMIN_PASSWORD": sample_text("sonar", "-value"),
                "TSW_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS": "30",
            }

            with patch.dict(os.environ, environment, clear=True):
                result = composition.build_configuration_validation_service(
                    env_file
                ).validate()

        self.assertTrue(result.passed)
        self.assertNotIn("file-secret", repr(result.to_dict()))
        self.assertNotIn(
            environment["TSW_NEXUS_ADMIN_PASSWORD"], repr(result.to_dict())
        )

    def test_build_configuration_validation_service_uses_install_env_file_override(
        self,
    ):
        with TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / "operator.env"
            env_file.write_text(
                "\n".join(
                    f"{key}='{value}'"
                    for key, value in {
                        **_required_infisical_bootstrap_env(),
                        "TSW_NEXUS_ADMIN_PASSWORD": sample_text("nexus", "-value"),
                        "TSW_SONARQUBE_ADMIN_PASSWORD": sample_text("sonar", "-value"),
                    }.items()
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ, {"TSW_INSTALL_ENV_FILE": str(env_file)}, clear=True
            ):
                result = composition.build_configuration_validation_service().validate()

        self.assertTrue(result.passed)

    def test_wsl_lxc_user_namespace_gate_allows_missing_kernel_flag(self):
        with patch.object(
            composition,
            "_linux_text_file_equals",
            side_effect=AssertionError("missing WSL kernel flag must not be read"),
        ):
            self.assertTrue(
                composition._wsl_unprivileged_userns_clone_available(
                    _ExistingPath(exists=False)
                )
            )

    def test_wsl_lxc_user_namespace_gate_honors_present_kernel_flag(self):
        with patch.object(
            composition,
            "_linux_text_file_equals",
            return_value=True,
        ) as text_file_equals:
            self.assertTrue(
                composition._wsl_unprivileged_userns_clone_available(
                    _ExistingPath(exists=True)
                )
            )

        text_file_equals.assert_called_once()

    def test_artifact_and_deployment_service_bundles_exist(self):
        artifact_field_names = {
            field.name for field in fields(composition.ArtifactServices)
        }
        artifact_workflow_names = {
            field.name for field in fields(composition.ArtifactWorkflows)
        }
        deployment_field_names = {
            field.name for field in fields(composition.DeploymentServices)
        }
        deployment_workflow_names = {
            field.name for field in fields(composition.DeploymentWorkflows)
        }
        setup_field_names = {field.name for field in fields(composition.SetupServices)}
        setup_workflow_names = {
            field.name for field in fields(composition.SetupWorkflows)
        }

        self.assertEqual({"workflows"}, artifact_field_names)
        self.assertEqual({"prepare", "verify"}, artifact_workflow_names)
        self.assertEqual({"workflows"}, deployment_field_names)
        self.assertEqual({"bootstrap", "apply", "verify"}, deployment_workflow_names)
        self.assertEqual({"workflows"}, setup_field_names)
        self.assertEqual({"run"}, setup_workflow_names)

    def test_build_platform_services_wires_preflight_adapter(self):
        with patch.object(
            composition,
            "NodeProviderConfigYamlRepository",
        ) as node_config_repository_factory:
            with patch.object(
                composition,
                "AsyncLxcNodeCommandRunner",
            ) as lxc_runner_factory:
                with patch.object(
                    composition,
                    "_wsl_lxc_lifecycle_capability_available",
                    return_value=True,
                ) as wsl_capability_probe:
                    services = composition.build_platform_services()

        self.assertEqual(node_config_repository_factory.call_count, 1)
        self.assertIn("project_paths", node_config_repository_factory.call_args.kwargs)
        lxc_runner_factory.assert_called_once_with()
        self.assertIsInstance(services.preflight, PreflightService)
        self.assertIsInstance(services.preflight.host_probe, HostPreflightProbe)
        self.assertIsInstance(services.lxc_node_provider, composition.LxcNodeProvider)
        self.assertIs(
            node_config_repository_factory.return_value,
            services.lxc_node_provider.config_repository,
        )
        self.assertIs(
            lxc_runner_factory.return_value,
            services.lxc_node_provider.runner,
        )
        self.assertIsInstance(
            services.node_provider_selection,
            composition.NodeProviderSelectionService,
        )
        self.assertIs(
            services.lxc_node_provider,
            services.node_provider_selection.node_lifecycle,
        )
        self.assertIs(
            services.lxc_node_provider,
            services.node_provider_selection.managed_node_teardown,
        )
        self.assertIs(
            wsl_capability_probe,
            services.node_provider_selection.readiness_probe.wsl_lxc_capability_available,
        )
        self.assertFalse(services.lxc_node_provider.allow_live_mutation)

    def test_build_platform_services_wires_workflow_objects(self):
        evidence_repository = _RecordingEvidenceRepository()
        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            services = composition.build_platform_services(
                trace_correlation_id="trace-test"
            )

        self.assertIsInstance(services.workflows.init, composition.PlatformInitWorkflow)
        self.assertIsInstance(
            services.workflows.reconcile, composition.PlatformReconcileWorkflow
        )
        self.assertIsInstance(
            services.workflows.expose, composition.PlatformExposeWorkflow
        )
        self.assertIsInstance(
            services.workflows.repair_lxc_proxy_drift,
            composition.PlatformRepairLxcProxyDriftWorkflow,
        )
        self.assertIsInstance(
            services.workflows.reset, composition.PlatformResetWorkflow
        )
        self.assertIsInstance(
            services.workflows.destroy, composition.PlatformDestroyWorkflow
        )
        self.assertIsInstance(
            services.workflows.verify, composition.PlatformVerifyWorkflow
        )
        self.assertIsInstance(services.workflows.cluster, composition.ClusterWorkflows)
        self.assertIsInstance(
            services.workflows.cluster.docker,
            composition.PlatformInitWorkflow,
        )
        self.assertIsInstance(
            services.workflows.cluster.swarm_bootstrap,
            composition.PlatformInitWorkflow,
        )
        self.assertIsInstance(
            services.workflows.cluster.verify,
            composition.PlatformVerifyWorkflow,
        )
        self.assertIs(
            evidence_repository,
            services.workflows.init.verification_evidence_repository,
        )
        self.assertIsNone(services.workflows.init.pre_apply_guard)
        self.assertIs(
            evidence_repository,
            services.workflows.reconcile.verification_evidence_repository,
        )
        self.assertIs(
            evidence_repository,
            services.workflows.expose.verification_evidence_repository,
        )
        self.assertIs(
            evidence_repository,
            services.workflows.repair_lxc_proxy_drift.verification_evidence_repository,
        )
        self.assertIsInstance(
            services.workflows.init.progress,
            composition.CompositeWorkflowProgress,
        )
        self.assertIsInstance(
            services.workflows.init.method_trace,
            composition.CompositeMethodTrace,
        )
        self.assertIs(
            services.workflows.init.progress,
            services.workflows.reconcile.progress,
        )
        self.assertIs(
            services.workflows.init.progress,
            services.workflows.expose.progress,
        )
        self.assertIs(
            services.workflows.init.progress,
            services.workflows.repair_lxc_proxy_drift.progress,
        )
        self.assertIs(
            services.workflows.init.method_trace,
            services.workflows.reconcile.method_trace,
        )
        self.assertIs(
            services.workflows.init.method_trace,
            services.workflows.expose.method_trace,
        )
        self.assertIs(
            services.workflows.init.method_trace,
            services.workflows.repair_lxc_proxy_drift.method_trace,
        )
        self.assertEqual(services.workflows.init.trace_correlation_id, "trace-test")
        self.assertEqual(
            services.workflows.reconcile.trace_correlation_id,
            "trace-test",
        )
        self.assertEqual(services.workflows.expose.trace_correlation_id, "trace-test")
        self.assertEqual(
            services.workflows.repair_lxc_proxy_drift.trace_correlation_id,
            "trace-test",
        )
        self.assertEqual(services.workflows.reset.trace_correlation_id, "trace-test")
        self.assertEqual(services.workflows.destroy.trace_correlation_id, "trace-test")
        self.assertEqual(services.workflows.verify.trace_correlation_id, "trace-test")

    def test_build_platform_services_wires_read_only_platform_verify_steps(self):
        services = composition.build_platform_services()

        verify_preflight = services.workflows.verify.steps[0]
        verify_steps = services.workflows.verify.steps

        self.assertIsInstance(verify_preflight, PreflightService)
        self.assertIsNot(services.preflight, verify_preflight)
        self.assertGreater(len(services.preflight.configuration.required_ports), 0)
        self.assertEqual(verify_preflight.configuration.required_ports, ())
        self.assertEqual(len(verify_steps), 6)
        self.assertTrue(
            all(
                isinstance(step, composition.NodeProviderVerifyNodeStep)
                for step in verify_steps[1:4]
            )
        )
        self.assertIsInstance(verify_steps[4], composition.LxcServiceExposureVerifyStep)
        self.assertEqual(
            composition.PortainerEndpointVerifyStep.verification_target_id,
            verify_steps[5].verification_target_id,
        )
        self.assertEqual(len(services.workflows.cluster.docker.steps), 1)
        self.assertIsInstance(
            services.workflows.cluster.docker.steps[0], composition.LxcDockerInstallStep
        )
        self.assertEqual(len(services.workflows.cluster.swarm_bootstrap.steps), 1)
        self.assertIsInstance(
            services.workflows.cluster.swarm_bootstrap.steps[0],
            composition.LxcSwarmBootstrapStep,
        )
        self.assertEqual(len(services.workflows.cluster.verify.steps), 2)
        self.assertIsInstance(
            services.workflows.cluster.verify.steps[0],
            composition.LxcDockerVerifyStep,
        )
        self.assertIsInstance(
            services.workflows.cluster.verify.steps[1],
            composition.LxcSwarmVerifyStep,
        )

    def test_build_platform_services_wires_reset_destroy_managed_node_steps(self):
        services = composition.build_platform_services()

        self.assertEqual(len(services.workflows.reset.steps), 1)
        self.assertEqual(len(services.workflows.destroy.steps), 1)
        reset_step = services.workflows.reset.steps[0]
        destroy_step = services.workflows.destroy.steps[0]

        self.assertIsInstance(reset_step, composition.NodeProviderResetManagedNodesStep)
        self.assertIsInstance(
            destroy_step, composition.NodeProviderDestroyManagedNodesStep
        )
        self.assertEqual(composition.DEFAULT_LXC_PLATFORM_NODES, reset_step.nodes)
        self.assertEqual(composition.DEFAULT_LXC_PLATFORM_NODES, destroy_step.nodes)
        self.assertIs(services.node_provider_selection, reset_step.provider_selection)
        self.assertIs(services.node_provider_selection, destroy_step.provider_selection)

    def test_build_platform_services_does_not_run_lxc_commands_during_wiring(self):
        async def fail_if_called(*_args, **_kwargs):
            raise AssertionError("composition must not run LXC commands during wiring")

        with patch.object(composition, "AsyncLxcNodeCommandRunner") as runner_factory:
            runner_factory.return_value.run.side_effect = fail_if_called

            services = composition.build_platform_services()

        runner_factory.assert_called_once_with()
        self.assertIsInstance(services.lxc_node_provider, composition.LxcNodeProvider)

    def test_build_platform_services_wires_workflow_types_without_evidence_patch(self):
        services = composition.build_platform_services()

        self.assertIsInstance(services.workflows.init, composition.PlatformInitWorkflow)
        self.assertIsInstance(
            services.workflows.reconcile, composition.PlatformReconcileWorkflow
        )
        self.assertIsInstance(
            services.workflows.expose, composition.PlatformExposeWorkflow
        )
        self.assertIsInstance(
            services.workflows.repair_lxc_proxy_drift,
            composition.PlatformRepairLxcProxyDriftWorkflow,
        )
        self.assertIsInstance(
            services.workflows.reset, composition.PlatformResetWorkflow
        )
        self.assertIsInstance(
            services.workflows.destroy, composition.PlatformDestroyWorkflow
        )
        self.assertIsInstance(
            services.workflows.verify, composition.PlatformVerifyWorkflow
        )

    def test_build_platform_services_adds_terminal_sinks_when_ui_is_supplied(self):
        ui = _RecordingUI()

        services = composition.build_platform_services(ui=ui)

        progress_sink = services.workflows.init.progress
        method_trace_sink = services.workflows.init.method_trace
        self.assertIsInstance(progress_sink, composition.CompositeWorkflowProgress)
        self.assertIsInstance(method_trace_sink, composition.CompositeMethodTrace)

        progress_sinks = cast(
            composition.CompositeWorkflowProgress, progress_sink
        ).sinks
        method_trace_sinks = cast(
            composition.CompositeMethodTrace, method_trace_sink
        ).sinks

        self.assertTrue(
            any(
                isinstance(sink, composition.TerminalWorkflowProgress) and sink.ui is ui
                for sink in progress_sinks
            )
        )
        self.assertTrue(
            any(
                isinstance(sink, composition.TerminalMethodTrace) and sink.ui is ui
                for sink in method_trace_sinks
            )
        )

    def test_build_setup_ui_uses_ui_factory_without_starting_thread(self):
        ui = _RecordingUI()

        with patch.object(composition, "FactoryUI") as factory:
            factory.return_value.get_ui.return_value = ui

            result = composition.build_setup_ui(test_mode=True)

        self.assertIs(ui, result)
        factory.return_value.get_ui.assert_called_once_with(
            instances=(),
            test_mode=True,
        )
        self.assertIsNone(ui.ui_thread)

    def test_run_setup_with_terminal_status_runs_composed_lifecycle_after_consent(self):
        calls: list[str] = []
        live_consent = _accepted_live_consent()
        recording_ui = _LifecycleRecordingUI(calls)
        result = _setup_result(SetupWorkflowStatus.COMPLETED)

        def build_setup_ui():
            calls.append("ui built")
            return recording_ui

        def build_setup_services(
            consent,
            *,
            service_profile,
            node_provider_request,
            ui,
            configuration_validation,
            allow_wsl_windows_filesystem,
        ):
            calls.append("services built")
            self.assertIs(live_consent, consent)
            self.assertEqual(ServiceStackProfile.SERVICE_ACCESS, service_profile)
            self.assertEqual(
                composition.NodeProviderSelectionRequest(), node_provider_request
            )
            self.assertIs(recording_ui, ui)
            self.assertIsNotNone(configuration_validation)
            self.assertFalse(allow_wsl_windows_filesystem)
            return _setup_lifecycle_bundle(calls, result)

        with patch.object(composition, "build_setup_ui", side_effect=build_setup_ui):
            with patch.object(
                composition,
                "build_setup_services",
                side_effect=build_setup_services,
            ):
                actual = asyncio.run(
                    composition.run_setup_with_terminal_status(
                        live_consent,
                        "run",
                        service_profile=ServiceStackProfile.SERVICE_ACCESS,
                        node_provider_request=composition.NodeProviderSelectionRequest(),
                    )
                )

        self.assertIs(result, actual)
        self.assertEqual(
            calls,
            [
                "ui built",
                "ui started",
                "services built",
                "workflow run",
                "ui update completed",
                "ui awaited",
            ],
        )
        self.assertEqual(
            SetupWorkflowStatus.COMPLETED.value,
            recording_ui.aggregate_status["result"],
        )

    def test_run_setup_with_terminal_status_rejects_missing_consent_before_ui(self):
        live_consent = LiveConsent(live_flag=False)

        with patch.object(composition, "build_setup_ui") as build_setup_ui:
            with self.assertRaises(ValueError):
                asyncio.run(
                    composition.run_setup_with_terminal_status(
                        live_consent,
                        "run",
                    )
                )

        build_setup_ui.assert_not_called()

    def test_run_setup_with_terminal_status_marks_ui_error_when_workflow_raises(self):
        calls: list[str] = []
        ui = _LifecycleRecordingUI(calls)

        with patch.object(composition, "build_setup_ui", return_value=ui):
            with patch.object(
                composition,
                "build_setup_services",
                return_value=_setup_lifecycle_bundle(
                    calls,
                    RuntimeError("boom"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(
                        composition.run_setup_with_terminal_status(
                            _accepted_live_consent(),
                            "run",
                        )
                    )

        self.assertIn(
            (AGGREGATE_INSTANCE, "setup run", "exception", STATUS_ERROR),
            ui.updates,
        )
        self.assertEqual(STATUS_ERROR, ui.aggregate_status["result"])
        self.assertIn("ui awaited", calls)

    def test_run_setup_with_terminal_status_preserves_aggregate_failure(self):
        calls: list[str] = []
        ui = _LifecycleRecordingUI(calls)
        result = _setup_result(SetupWorkflowStatus.COMPLETED)

        with patch.object(composition, "build_setup_ui", return_value=ui):
            with patch.object(
                composition,
                "build_setup_services",
                return_value=_setup_lifecycle_bundle(
                    calls,
                    result,
                    ui=ui,
                    status_updates=(
                        SetupWorkflowStatus.BLOCKED.value,
                        STATUS_SUCCESS,
                    ),
                ),
            ):
                actual = asyncio.run(
                    composition.run_setup_with_terminal_status(
                        _accepted_live_consent(),
                        "run",
                    )
                )

        self.assertIs(result, actual)
        self.assertEqual(STATUS_ERROR, ui.aggregate_status["result"])

    def test_build_artifact_services_wires_artifact_contracts_without_running_clients(
        self,
    ):
        with patch.dict(os.environ, {}, clear=True):
            services = composition.build_lxc_artifact_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        self.assertIsInstance(
            services.workflows.prepare, composition.ArtifactPrepareWorkflow
        )
        self.assertIsInstance(
            services.workflows.verify, composition.ArtifactVerifyWorkflow
        )
        self.assertEqual(
            tuple(
                step.verification_target_id for step in services.workflows.prepare.steps
            ),
            (
                "artifacts:nexus-ready",
                "artifacts:nexus-admin-access",
                "artifacts:nexus-docker-hosted-repository",
                "artifacts:nexus-docker-hub-proxy-repository",
                "artifacts:nexus-maven-proxy-repository",
                "artifacts:jenkins-image",
                "artifacts:service-access-dashboard-image",
                "artifacts:service-access-nginx-image",
                "artifacts:infisical-image",
                "artifacts:infisical-postgres-image",
                "artifacts:infisical-redis-image",
                "artifacts:traefik-image",
                "artifacts:sonarqube-image",
                "artifacts:sonarqube-postgres-image",
                "artifacts:swagger-editor-image",
                "artifacts:swagger-ui-image",
                "artifacts:pulsar-image",
                "artifacts:pulsar-manager-image",
                "artifacts:pulsar-manager-bootstrap-image",
                "artifacts:swagger-nginx-image",
                "artifacts:portainer-image",
                "artifacts:portainer-agent-image",
                "artifacts:nexus-image",
                "artifacts:swagger-api-image",
            ),
        )

    def test_nexus_docker_proxy_remote_url_uses_lxc_registry_mirror(self):
        with patch.dict(
            os.environ,
            {
                "TSW_LXC_DOCKER_REGISTRY_MIRROR": sample_http_url(
                    ipv4_address(10, 0, 3, 1),
                    5001,
                )
            },
            clear=True,
        ):
            remote_url = composition._nexus_docker_proxy_remote_url()

        self.assertEqual(
            sample_http_url(ipv4_address(10, 0, 3, 1), 5001),
            remote_url,
        )

    def test_build_artifact_services_sets_internal_nexus_proxy_to_lxc_registry_mirror(
        self,
    ):
        with patch.dict(
            os.environ,
            {
                "TSW_LXC_DOCKER_REGISTRY_MIRROR": sample_http_url(
                    ipv4_address(10, 0, 3, 1),
                    5001,
                )
            },
            clear=True,
        ):
            services = composition.build_lxc_artifact_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        proxy_step = services.workflows.prepare.steps[3]
        proxy_configuration = getattr(proxy_step, "configuration")

        self.assertEqual(
            getattr(proxy_step, "verification_target_id"),
            "artifacts:nexus-docker-hub-proxy-repository",
        )
        self.assertEqual(
            sample_http_url(ipv4_address(10, 0, 3, 1), 5001),
            proxy_configuration.remote_url,
        )

    def test_nexus_docker_proxy_remote_url_falls_back_to_docker_hub_without_mirror(
        self,
    ):
        with patch.dict(os.environ, {}, clear=True):
            remote_url = composition._nexus_docker_proxy_remote_url()

        self.assertEqual(remote_url, "https://registry-1.docker.io")

    def test_build_artifact_services_uses_infisical_image_overrides(self):
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_NEXUS_ADMIN_PASSWORD": sample_text("nexus", "-value"),
                "TSW_INFISICAL_IMAGE": "registry.local:5000/infisical:cached",
                "TSW_INFISICAL_POSTGRES_IMAGE": "registry.local:5000/postgres:14-alpine",
                "TSW_INFISICAL_REDIS_IMAGE": "registry.local:5000/redis:7-alpine",
            },
            clear=True,
        ):
            services = composition.build_lxc_artifact_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        image_refs = {
            step.contract.build_context: step.contract.image_ref
            for step in services.workflows.prepare.steps
            if hasattr(step, "contract")
        }

        self.assertEqual(
            image_refs["infisical"], "registry.local:5000/infisical:cached"
        )
        self.assertEqual(
            image_refs["infisical-postgres"],
            "registry.local:5000/postgres:14-alpine",
        )
        self.assertEqual(
            image_refs["infisical-redis"], "registry.local:5000/redis:7-alpine"
        )

    def test_build_artifact_services_keeps_docker_hub_image_refs_for_mirror_defaults(
        self,
    ):
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_NEXUS_ADMIN_PASSWORD": sample_text("nexus", "-value"),
            },
            clear=True,
        ):
            services = composition.build_lxc_artifact_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        image_refs = {
            step.contract.build_context: step.contract.image_ref
            for step in services.workflows.prepare.steps
            if hasattr(step, "contract")
        }

        self.assertEqual(image_refs["infisical"], "infisical/infisical:v0.159.1")
        self.assertEqual(image_refs["infisical-postgres"], "postgres:14.23-alpine3.23")
        self.assertEqual(image_refs["infisical-redis"], "redis:7.4.9-alpine3.21")
        self.assertEqual(image_refs["traefik"], "traefik:v3.7.4")
        self.assertEqual(image_refs["sonarqube"], "sonarqube:26.6.0.123539-community")
        self.assertEqual(image_refs["sonarqube-postgres"], "postgres:13.23")
        self.assertEqual(
            image_refs["swagger-editor"],
            "swaggerapi/swagger-editor:v5.6.2-unprivileged",
        )
        self.assertEqual(image_refs["swagger-ui"], "swaggerapi/swagger-ui:v5.32.6")
        self.assertEqual(image_refs["pulsar"], "apachepulsar/pulsar:3.0.17")
        self.assertEqual(
            image_refs["pulsar-manager"], "apachepulsar/pulsar-manager:v0.4.0"
        )
        self.assertEqual(
            image_refs["pulsar-manager-bootstrap"], "python:3.12.13-alpine3.23"
        )
        self.assertEqual(image_refs["swagger-nginx"], "nginx:1.29.8-alpine")

    def test_all_supported_image_overrides_update_artifact_contracts(self):
        overrides = {
            "nexus": "TSW_NEXUS_IMAGE",
            "jenkins": "TSW_JENKINS_IMAGE",
            "service-access-dashboard": "TSW_SERVICE_ACCESS_DASHBOARD_IMAGE",
            "service-access-nginx": "TSW_SERVICE_ACCESS_NGINX_IMAGE",
            "pulsar": "TSW_PULSAR_IMAGE",
            "pulsar-manager": "TSW_PULSAR_MANAGER_IMAGE",
            "pulsar-manager-bootstrap": "TSW_PULSAR_MANAGER_BOOTSTRAP_IMAGE",
            "infisical": "TSW_INFISICAL_IMAGE",
            "infisical-postgres": "TSW_INFISICAL_POSTGRES_IMAGE",
            "infisical-redis": "TSW_INFISICAL_REDIS_IMAGE",
            "traefik": "TSW_TRAEFIK_IMAGE",
        }
        environment = {
            environment_name: f"registry.local/{context}:9.9.9"
            for context, environment_name in overrides.items()
        }

        with patch.dict(os.environ, environment, clear=True):
            contracts = composition._container_image_contracts_from_environment()

        image_refs = {contract.build_context: contract.image_ref for contract in contracts}
        for context in overrides:
            with self.subTest(context=context):
                self.assertEqual(image_refs[context], f"registry.local/{context}:9.9.9")

    def test_build_artifact_services_does_not_call_live_clients_during_construction(
        self,
    ):
        services = composition.build_lxc_artifact_services(
            backend=composition.ManagedLxcBackend.INCUS,
        )

        self.assertEqual(len(services.workflows.prepare.steps), 24)
        self.assertEqual(len(services.workflows.verify.checks), 24)

    def test_build_deployment_services_wires_stack_contracts_without_running_runtime(
        self,
    ):
        with patch.dict("os.environ", _required_infisical_bootstrap_env(), clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        self.assertIsInstance(
            services.workflows.bootstrap, composition.DeploymentApplyWorkflow
        )
        self.assertIsInstance(
            services.workflows.apply, composition.DeploymentApplyWorkflow
        )
        self.assertIsInstance(
            services.workflows.verify, composition.DeploymentVerifyWorkflow
        )
        self.assertEqual(
            tuple(
                step.verification_target_id
                for step in services.workflows.bootstrap.steps
            ),
            (
                "deployment:portainer-stack",
                "deployment:portainer-admin-access",
                "deployment:portainer-local-endpoint",
                "deployment:nexus-stack",
            ),
        )

    def test_traefik_gui_operator_input_is_prepared_then_verified_without_disclosure(self):
        operator_value = (
            "admin:$2y$12$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        environment = {
            **_required_infisical_bootstrap_env(),
            "TSW_TRAEFIK_GUI_USERS_HTPASSWD": operator_value,
        }
        with patch.dict("os.environ", environment, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        ensure_step = services.workflows.apply.pre_apply_steps[0]
        verifier = services.workflows.apply.pre_apply_checks[0]
        self.assertEqual(ensure_step.verification_target_id, "deployment:traefik-gui-input")
        self.assertEqual(verifier.verification_target_id, "deployment:traefik-gui-input")
        ensure_runtime = Mock()
        ensure_step.swarm_runtime = ensure_runtime
        ensure_step.run()
        ensure_runtime.ensure_external_secret.assert_called_once_with(
            "tsw_traefik_gui_users", operator_value
        )

        verifier.swarm_runtime = Mock(external_secret_exists=Mock(return_value=False))
        verification = asyncio.run(verifier.verify())
        serialized = str(verification.to_dict())
        self.assertNotIn(operator_value, serialized)
        self.assertNotIn("AAAAAAAA", serialized)
        stack_apply = Mock()
        blocked_workflow = composition.DeploymentApplyWorkflow(
            steps=(stack_apply,),
            pre_apply_checks=(verifier,),
        )
        blocked_result = asyncio.run(blocked_workflow.run())
        stack_apply.run.assert_not_called()
        self.assertNotIn(operator_value, str(blocked_result))
        self.assertEqual(
            tuple(
                step.verification_target_id for step in services.workflows.apply.steps
            ),
            (
                "deployment:traefik-stack",
                "deployment:infisical-stack",
                "deployment:service-access-stack",
                "deployment:infisical-bootstrap-service-readiness",
                "deployment:infisical-bootstrap-access-readiness",
                "deployment:managed-config-inventory",
                "deployment:infisical-silent-install",
                "deployment:infisical-sync",
                "deployment:managed-config-consumption",
                "deployment:managed-config-evidence",
                "deployment:jenkins-stack",
                "deployment:pulsar-stack",
                "deployment:sonarqube-stack",
                "deployment:sonarqube-admin-access",
                "deployment:swagger-stack",
            ),
        )
        self.assertTrue(
            all(
                isinstance(step, EnsureSwarmStack)
                for step in services.workflows.apply.steps
                if step.verification_target_id.endswith("-stack")
            )
        )
        jenkins_step = next(
            step
            for step in services.workflows.apply.steps
            if hasattr(step, "service_stack")
            and step.service_stack.stack_name == "jenkins"
        )
        nexus_step = next(
            step
            for step in services.workflows.bootstrap.steps
            if hasattr(step, "service_stack")
            and step.service_stack.stack_name == "nexus"
        )
        self.assertEqual(
            nexus_step.stack_environment,
            {"TSW_NEXUS_IMAGE": "sonatype/nexus3:3.75.1"},
        )
        self.assertEqual(
            jenkins_step.stack_environment,
            {
                "TSW_JENKINS_ADMIN_PASSWORD": sample_text("jenkins", "-value"),
                "TSW_JENKINS_IMAGE": "127.0.0.1:13500/jenkins:0.2.0",
            },
        )
        traefik_step = next(
            step
            for step in services.workflows.apply.steps
            if hasattr(step, "service_stack")
            and step.service_stack.stack_name == "traefik"
        )
        self.assertEqual(
            traefik_step.stack_environment,
            {
                "TSW_TRAEFIK_IMAGE": "traefik:v3.7.4",
                "TSW_TRAEFIK_TLS_CERT_SECRET_NAME": "tsw_traefik_tls_cert",
                "TSW_TRAEFIK_TLS_KEY_SECRET_NAME": "tsw_traefik_tls_key",
                "TSW_TRAEFIK_GUI_USERS_SECRET_NAME": "tsw_traefik_gui_users",
            },
        )
        sonarqube_admin_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:sonarqube-admin-access"
        )
        self.assertEqual(
            sample_text("sonar-admin", "-value!"),
            sonarqube_admin_step.password,
        )
        self.assertEqual(
            sonarqube_admin_step.sonarqube_client.base_url, "http://localhost:12000"
        )
        consumption_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:managed-config-consumption"
        )
        self.assertEqual(
            consumption_step.non_stack_consumer_refs,
            {
                "TSW_NEXUS_ADMIN_PASSWORD": "artifacts:nexus-admin-access",
                "TSW_PORTAINER_ADMIN_PASSWORD": "deployment:portainer-admin-access",
                "TSW_SONARQUBE_ADMIN_PASSWORD": "deployment:sonarqube-admin-access",
            },
        )
        self.assertEqual(
            tuple(
                check.verification_target_id
                for check in services.workflows.verify.checks
            ),
            (
                "deployment:portainer-service-readiness",
                "deployment:traefik-service-readiness",
                "deployment:nexus-service-readiness",
                "deployment:jenkins-service-readiness",
                "deployment:pulsar-service-readiness",
                "deployment:sonarqube-service-readiness",
                "deployment:swagger-service-readiness",
                "deployment:infisical-service-readiness",
                "deployment:service-access-service-readiness",
            ),
        )
        self.assertEqual(
            tuple(
                check.verification_target_id
                for check in services.workflows.apply.pre_apply_checks
            ),
            ("deployment:traefik-gui-input",),
        )
        self.assertEqual(
            tuple(
                step.deployment_target_id
                for step in services.workflows.apply.pre_apply_steps
            ),
            (
                "deployment:traefik-gui-input",
                "deployment:effective-access-model-evidence",
                "deployment:traefik-stack-assets",
                "deployment:swagger-stack-assets",
                "deployment:service-access-stack-assets",
            ),
        )

    def test_build_deployment_services_wires_service_access_dashboard_renderer_to_swarm_runtime(
        self,
    ):
        with patch.object(
            composition, "ComposeFileRepositoryYaml"
        ) as compose_repository:
            with patch.object(composition, "LxcSwarmRuntime") as swarm_runtime:
                composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        self.assertIs(
            compose_repository.return_value.render_service_access_dashboard,
            swarm_runtime.call_args.kwargs["service_access_dashboard_renderer"],
        )
        compose_repository.return_value.render_service_access_dashboard.assert_not_called()

    def test_build_deployment_services_injects_canonical_tls_resolver(self):
        with (
            patch.object(composition, "ComposeFileRepositoryYaml"),
            patch.object(composition, "LxcSwarmRuntime") as swarm_runtime,
            patch(
                "tiny_swarm_world.infrastructure.adapters.ingress."
                "local_tls_contract_resolver.LocalTlsContractResolver"
            ) as resolver,
        ):
            composition.build_lxc_deployment_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        self.assertIs(
            resolver.return_value,
            swarm_runtime.call_args.kwargs["tls_contract_resolver"],
        )

    def test_build_deployment_services_keeps_service_access_assets_out_of_default_profile(
        self,
    ):
        with patch.object(composition, "ComposeFileRepositoryYaml"):
            services = composition.build_lxc_deployment_services(
                backend=composition.ManagedLxcBackend.INCUS,
                service_profile=ServiceStackProfile.DEFAULT,
            )

        self.assertEqual(
            tuple(
                step.deployment_target_id
                for step in services.workflows.apply.pre_apply_steps
            ),
            (
                "deployment:effective-access-model-evidence",
                "deployment:traefik-stack-assets",
                "deployment:swagger-stack-assets",
            ),
        )

    def test_build_deployment_services_does_not_call_runtime_during_construction(self):
        with patch.object(
            composition, "ComposeFileRepositoryYaml"
        ) as compose_repository:
            services = composition.build_lxc_deployment_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        self.assertEqual(compose_repository.call_count, 1)
        self.assertIn("project_paths", compose_repository.call_args.kwargs)
        self.assertEqual(
            ServiceStackProfile.SERVICE_ACCESS,
            compose_repository.call_args.kwargs["service_profile"],
        )
        self.assertEqual(len(services.workflows.bootstrap.steps), 4)
        self.assertEqual(len(services.workflows.apply.steps), 15)
        self.assertEqual(len(services.workflows.verify.checks), 9)

    def test_only_service_access_jenkins_consumes_completed_sync_snapshot(self):
        from tiny_swarm_world.application.services.deployment.secret_management import SecretManagementBlocker

        for profile in (ServiceStackProfile.DEFAULT, ServiceStackProfile.SERVICE_ACCESS):
            with self.subTest(profile=profile), patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS, service_profile=profile)
                steps = services.workflows.apply.steps
                consumers = [step for step in steps if isinstance(step, composition.EnsureSwarmStack)
                             and step.credential_snapshot is not None]
                if profile is ServiceStackProfile.DEFAULT:
                    self.assertEqual(consumers, [])
                    continue
                self.assertEqual(len(consumers), 1)
                jenkins = consumers[0]
                sync = next(step for step in steps if isinstance(step, composition.InfisicalSecretSyncStep))
                self.assertEqual(jenkins.service_stack.stack_name, "jenkins")
                self.assertEqual(jenkins.credential_keys, ("TSW_JENKINS_ADMIN_PASSWORD",))
                self.assertIs(jenkins.credential_snapshot.func.__self__, sync)
                self.assertLess(steps.index(sync), steps.index(jenkins))
                self.assertTrue(all(getattr(step, "credential_snapshot", None) is None
                                    for step in services.workflows.bootstrap.steps))
                with patch.object(jenkins.swarm_runtime, "deploy_stack") as deploy:
                    with self.assertRaises(SecretManagementBlocker):
                        asyncio.run(jenkins.run())
                deploy.assert_not_called()

    def test_deployment_kernel_guard_is_native_only_and_covers_bootstrap(self):
        from tiny_swarm_world.domain.host_environment import HostEnvironmentKind
        from tiny_swarm_world.infrastructure import composition_deployment

        for kind in HostEnvironmentKind:
            with self.subTest(kind=kind), patch.object(
                composition_deployment, "HostEnvironmentDetector"
            ) as detector, patch.object(composition, "ComposeFileRepositoryYaml"):
                detector.return_value.detect.return_value.environment = kind
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )
                for workflow in (services.workflows.bootstrap, services.workflows.apply):
                    self.assertEqual(len(workflow.prerequisite_checks),
                                     0 if kind is HostEnvironmentKind.WSL2 else 1)
                    if kind not in (HostEnvironmentKind.NATIVE_LINUX, HostEnvironmentKind.WSL2):
                        self.assertEqual(workflow.prerequisite_checks[0].verify().status,
                                         VerificationStatus.BLOCKED)

    def test_default_provider_artifact_services_use_lxc_clients_when_backend_is_available(
        self,
    ):
        with patch.object(composition.shutil, "which", return_value="/usr/bin/lxc"):
            services = composition.build_artifact_services_for_provider()

        self.assertIsInstance(
            services.workflows.prepare, composition.ArtifactPrepareWorkflow
        )
        self.assertEqual(len(services.workflows.prepare.steps), 24)

    def test_default_provider_deployment_services_use_lxc_clients_when_backend_is_available(
        self,
    ):
        with patch.object(composition.shutil, "which", return_value="/usr/bin/incus"):
            services = composition.build_deployment_services_for_provider()

        self.assertIsInstance(
            services.workflows.bootstrap, composition.DeploymentApplyWorkflow
        )
        self.assertEqual(
            tuple(
                step.verification_target_id
                for step in services.workflows.bootstrap.steps
            ),
            (
                "deployment:portainer-stack",
                "deployment:portainer-admin-access",
                "deployment:portainer-local-endpoint",
                "deployment:nexus-stack",
            ),
        )

    def test_default_provider_deployment_services_fail_closed_without_lxc_backend(self):
        with patch.object(composition.shutil, "which", return_value=None):
            services = composition.build_deployment_services_for_provider()

        result = asyncio.run(services.workflows.apply.run())

        self.assertEqual(result.status.value, "blocked")

    def test_build_deployment_services_uses_named_portainer_api_default(self):
        services = composition.build_lxc_deployment_services(
            backend=composition.ManagedLxcBackend.INCUS,
        )
        self.assertIsInstance(
            services.workflows.apply, composition.DeploymentApplyWorkflow
        )

    def test_build_deployment_services_can_select_service_access_profile(self):
        with patch.object(composition, "ComposeFileRepositoryYaml"):
            services = composition.build_lxc_deployment_services(
                backend=composition.ManagedLxcBackend.INCUS,
                service_profile=ServiceStackProfile.SERVICE_ACCESS,
            )

        self.assertEqual(
            tuple(
                step.verification_target_id
                for step in services.workflows.bootstrap.steps
            ),
            (
                "deployment:portainer-stack",
                "deployment:portainer-admin-access",
                "deployment:portainer-local-endpoint",
                "deployment:nexus-stack",
            ),
        )
        self.assertEqual(
            tuple(
                step.verification_target_id for step in services.workflows.apply.steps
            ),
            (
                "deployment:traefik-stack",
                "deployment:infisical-stack",
                "deployment:service-access-stack",
                "deployment:infisical-bootstrap-service-readiness",
                "deployment:infisical-bootstrap-access-readiness",
                "deployment:managed-config-inventory",
                "deployment:infisical-silent-install",
                "deployment:infisical-sync",
                "deployment:managed-config-consumption",
                "deployment:managed-config-evidence",
                "deployment:jenkins-stack",
                "deployment:pulsar-stack",
                "deployment:sonarqube-stack",
                "deployment:sonarqube-admin-access",
                "deployment:swagger-stack",
            ),
        )
        self.assertTrue(
            all(
                isinstance(step, EnsureSwarmStack)
                for step in services.workflows.apply.steps
                if step.verification_target_id.endswith("-stack")
            )
        )
        self.assertEqual(
            tuple(
                check.verification_target_id
                for check in services.workflows.verify.checks
            ),
            (
                "deployment:portainer-service-readiness",
                "deployment:traefik-service-readiness",
                "deployment:nexus-service-readiness",
                "deployment:jenkins-service-readiness",
                "deployment:pulsar-service-readiness",
                "deployment:sonarqube-service-readiness",
                "deployment:swagger-service-readiness",
                "deployment:infisical-service-readiness",
                "deployment:service-access-service-readiness",
            ),
        )

    def test_build_deployment_services_wires_service_access_infisical_environment(self):
        stack_env = {
            **_required_infisical_bootstrap_env(),
            "TSW_INFISICAL_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
            "TSW_INFISICAL_AUTH_SECRET": sample_text("auth", "-secret"),
            "TSW_INFISICAL_POSTGRES_PASSWORD": sample_text("pg", "-secret"),
        }
        with patch.dict(
            "os.environ",
            stack_env,
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        service_access_step = next(
            step
            for step in services.workflows.apply.steps
            if step.service_stack.stack_name == "service-access"
        )
        infisical_step = next(
            step
            for step in services.workflows.apply.steps
            if step.service_stack.stack_name == "infisical"
        )

        self.assertEqual(
            service_access_step.stack_environment,
            {
                "TSW_SERVICE_ACCESS_DASHBOARD_IMAGE": (
                    "127.0.0.1:13500/service-access-dashboard:0.2.0"
                ),
                "TSW_SERVICE_ACCESS_NGINX_IMAGE": (
                    "127.0.0.1:13500/service-access-nginx:0.2.0"
                ),
            },
        )
        self.assertEqual(
            infisical_step.stack_environment,
            {
                "TSW_INFISICAL_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
                "TSW_INFISICAL_AUTH_SECRET": sample_text("auth", "-secret"),
                "TSW_INFISICAL_LOGIN_EMAIL": "admin@example.com",
                "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD": sample_text(
                    "master", "-value"
                ),
                "TSW_INFISICAL_ADMIN_FIRST_NAME": "Tiny",
                "TSW_INFISICAL_ADMIN_LAST_NAME": "Admin",
                "TSW_INFISICAL_POSTGRES_PASSWORD": sample_text("pg", "-secret"),
                "TSW_INFISICAL_REDIS_PASSWORD": sample_text("redis", "-secret"),
            },
        )
        self.assertEqual(
            tuple(
                check.verification_target_id
                for check in services.workflows.apply.pre_apply_checks
            ),
            ("deployment:traefik-gui-input",),
        )
        self.assertEqual(
            tuple(
                step.deployment_target_id
                for step in services.workflows.apply.pre_apply_steps
            ),
            (
                "deployment:effective-access-model-evidence",
                "deployment:traefik-stack-assets",
                "deployment:swagger-stack-assets",
                "deployment:service-access-stack-assets",
            ),
        )

    def test_build_deployment_services_wires_routing_evidence_from_selected_model_profile(
        self,
    ):
        with patch.object(
            composition, "ComposeFileRepositoryYaml"
        ) as compose_repository:
            with patch.object(
                composition,
                "RoutingEvidenceLocalRepository",
            ) as evidence_repository:
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.DEFAULT,
                )

        compose_repository.assert_called_once()
        self.assertEqual(
            ServiceStackProfile.DEFAULT,
            compose_repository.call_args.kwargs["service_profile"],
        )
        evidence_repository.assert_called_once_with(
            project_paths=compose_repository.call_args.kwargs["project_paths"]
        )
        evidence_step = services.workflows.apply.pre_apply_steps[0]
        self.assertIsInstance(
            evidence_step,
            composition.WriteEffectiveAccessModelEvidence,
        )
        self.assertIs(
            compose_repository.return_value,
            evidence_step.effective_access_model_repository,
        )
        self.assertIs(
            evidence_repository.return_value,
            evidence_step.routing_evidence_repository,
        )
        self.assertEqual(ServiceStackProfile.DEFAULT, evidence_step.service_profile)
        self.assertEqual(
            evidence_step.deployment_target_id,
            "deployment:effective-access-model-evidence",
        )

    def test_routing_evidence_failure_stops_apply_before_any_stack_step(self):
        from tiny_swarm_world.domain.host_environment import HostEnvironmentKind
        from tiny_swarm_world.infrastructure import composition_deployment

        for kind in (HostEnvironmentKind.NATIVE_LINUX, HostEnvironmentKind.WSL2):
            with self.subTest(kind=kind), patch.object(
                composition_deployment, "HostEnvironmentDetector"
            ) as detector, patch.object(
                composition_deployment, "NativeLinuxHostPreparation"
            ) as host, patch.object(composition, "ComposeFileRepositoryYaml"):
                detector.return_value.detect.return_value.environment = kind
                host_result = host.return_value.verify.return_value
                host_result.succeeded = True
                host_result.verified = True
                host_result.evidence = {}
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )
                evidence_step = services.workflows.apply.pre_apply_steps[0]
                first_stack_step = services.workflows.apply.steps[0]

                with patch.object(
                    evidence_step,
                    "run",
                    side_effect=OSError("evidence write failed"),
                ) as write_evidence, patch.object(first_stack_step, "run") as run_stack:
                    result = asyncio.run(services.workflows.apply.run())

                self.assertEqual(result.status.value, "failed_to_prepare")
                write_evidence.assert_called_once_with()
                run_stack.assert_not_called()
                self.assertEqual(host.return_value.verify.call_count,
                                 1 if kind is HostEnvironmentKind.NATIVE_LINUX else 0)

    def test_build_deployment_services_uses_operator_swarm_registry_endpoint_for_local_images(
        self,
    ):
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_SWARM_REGISTRY_ENDPOINT": "registry.local:5000",
            },
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        environments = {
            step.service_stack.stack_name: step.stack_environment
            for step in services.workflows.apply.steps
            if hasattr(step, "service_stack") and hasattr(step, "stack_environment")
        }

        self.assertEqual(
            environments["jenkins"]["TSW_JENKINS_IMAGE"],
            "registry.local:5000/jenkins:0.2.0",
        )
        self.assertEqual(
            environments["service-access"]["TSW_SERVICE_ACCESS_DASHBOARD_IMAGE"],
            "registry.local:5000/service-access-dashboard:0.2.0",
        )
        self.assertEqual(
            environments["service-access"]["TSW_SERVICE_ACCESS_NGINX_IMAGE"],
            "registry.local:5000/service-access-nginx:0.2.0",
        )

    def test_build_deployment_services_uses_operator_nexus_image_override(self):
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_NEXUS_IMAGE": "registry.local:5000/sonatype/nexus3:3.75.1",
            },
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        nexus_step = next(
            step
            for step in services.workflows.bootstrap.steps
            if hasattr(step, "service_stack")
            and step.service_stack.stack_name == "nexus"
        )

        self.assertEqual(
            nexus_step.stack_environment["TSW_NEXUS_IMAGE"],
            "registry.local:5000/sonatype/nexus3:3.75.1",
        )

    def test_build_artifact_services_uses_operator_environment_credentials(self):
        operator_value = sample_text("operator", "-supplied")
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_NEXUS_ADMIN_PASSWORD": operator_value,
            },
            clear=True,
        ):
            services = composition.build_lxc_artifact_services(
                backend=composition.ManagedLxcBackend.INCUS,
            )

        image_publisher = services.workflows.prepare.steps[-1].image_publisher
        self.assertEqual(
            operator_value,
            image_publisher.registry_password,
        )

    def test_build_deployment_services_uses_operator_portainer_credential(self):
        operator_value = sample_text("operator", "-portainer")
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_PORTAINER_ADMIN_PASSWORD": operator_value,
            },
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        self.assertEqual(operator_value, services.workflows.bootstrap.steps[1].password)

    def test_build_deployment_services_uses_operator_portainer_stack_timeout(self):
        with patch.dict(
            "os.environ",
            {
                **_required_infisical_bootstrap_env(),
                "TSW_PORTAINER_ADMIN_PASSWORD": sample_text("portainer", "-value"),
                "TSW_PORTAINER_STACK_REQUEST_TIMEOUT_SECONDS": "181",
            },
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                )

        endpoint_step = services.workflows.bootstrap.steps[2]
        self.assertEqual(
            endpoint_step.portainer_client.stack_request_timeout_seconds, 181
        )

    def test_build_deployment_services_can_seed_infisical_items_when_enabled(self):
        env = {
            **_required_infisical_bootstrap_env(),
            "TSW_SEED_INFISICAL_ITEMS": "1",
            "TSW_JENKINS_ADMIN_PASSWORD": sample_text("jenkins", "-value"),
            "TSW_NEXUS_ADMIN_PASSWORD": sample_text("nexus", "-value"),
            "TSW_PORTAINER_ADMIN_PASSWORD": sample_text("portainer", "-value"),
            "TSW_SONARQUBE_ADMIN_PASSWORD": sample_text("sonarqube", "-value"),
        }
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.SERVICE_ACCESS,
                )

        bootstrap_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:infisical-silent-install"
        )
        seed_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:infisical-items"
        )
        self.assertEqual(
            bootstrap_step.verification_target_id, "deployment:infisical-silent-install"
        )
        self.assertEqual(
            tuple(item.item_name for item in seed_step.items),
            (
                "platform/jenkins",
                "platform/nexus",
                "platform/portainer",
                "platform/pulsar",
                "platform/pulsar-manager",
                "platform/sonarqube",
            ),
        )

    def test_build_deployment_services_waits_for_infisical_before_silent_install(self):
        env = _required_infisical_bootstrap_env()
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.SERVICE_ACCESS,
                )

        target_ids = tuple(
            step.verification_target_id for step in services.workflows.apply.steps
        )
        service_guard_index = target_ids.index(
            "deployment:infisical-bootstrap-service-readiness"
        )
        access_guard_index = target_ids.index(
            "deployment:infisical-bootstrap-access-readiness"
        )
        bootstrap_index = target_ids.index("deployment:infisical-silent-install")

        self.assertLess(service_guard_index, bootstrap_index)
        self.assertLess(access_guard_index, bootstrap_index)
        self.assertIsInstance(
            services.workflows.apply.steps[service_guard_index],
            composition.EndpointReadinessCheck,
        )

    def test_service_access_sync_uses_catalog_backed_credentials(self):
        env = {
            **_required_infisical_bootstrap_env(),
        }
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.SERVICE_ACCESS,
                )

        sync_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:infisical-sync"
        )
        self.assertEqual(
            env["TSW_INFISICAL_LOGIN_EMAIL"],
            sync_step.use_case.process_environment["TSW_INFISICAL_LOGIN_EMAIL"],
        )

    def test_default_profile_does_not_construct_infisical_sync(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.DEFAULT,
                )

        target_ids = tuple(
            step.verification_target_id for step in services.workflows.apply.steps
        )
        self.assertNotIn("deployment:infisical-sync", target_ids)

    def test_build_deployment_services_uses_configurable_infisical_readiness_window(
        self,
    ):
        env = {
            **_required_infisical_bootstrap_env(),
            "TSW_INFISICAL_READINESS_ATTEMPTS": "240",
            "TSW_INFISICAL_READINESS_INTERVAL_SECONDS": "2.5",
        }
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.SERVICE_ACCESS,
                )

        bootstrap_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:infisical-silent-install"
        )
        self.assertEqual(
            bootstrap_step.verification_target_id, "deployment:infisical-silent-install"
        )
        self.assertEqual(bootstrap_step.bootstrap_client.readiness_attempts, 240)
        self.assertEqual(
            bootstrap_step.bootstrap_client.readiness_interval_seconds, 2.5
        )

    def test_build_deployment_services_uses_extended_infisical_readiness_default(self):
        env = _required_infisical_bootstrap_env()
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                services = composition.build_lxc_deployment_services(
                    backend=composition.ManagedLxcBackend.INCUS,
                    service_profile=ServiceStackProfile.SERVICE_ACCESS,
                )

        bootstrap_step = next(
            step
            for step in services.workflows.apply.steps
            if step.verification_target_id == "deployment:infisical-silent-install"
        )
        self.assertEqual(
            bootstrap_step.verification_target_id, "deployment:infisical-silent-install"
        )
        self.assertEqual(
            composition.DEFAULT_INFISICAL_READINESS_ATTEMPTS,
            bootstrap_step.bootstrap_client.readiness_attempts,
        )
        self.assertEqual(
            composition.DEFAULT_INFISICAL_READINESS_INTERVAL_SECONDS,
            bootstrap_step.bootstrap_client.readiness_interval_seconds,
        )
        self.assertTrue(bootstrap_step.bootstrap_client.verify_tls)

    def test_build_deployment_services_rejects_invalid_infisical_readiness_window(self):
        env = {
            **_required_infisical_bootstrap_env(),
            "TSW_INFISICAL_READINESS_ATTEMPTS": "0",
        }
        with patch.dict("os.environ", env, clear=True):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                with self.assertRaises(ValueError):
                    composition.build_lxc_deployment_services(
                        backend=composition.ManagedLxcBackend.INCUS,
                        service_profile=ServiceStackProfile.SERVICE_ACCESS,
                    )

    def test_build_deployment_services_rejects_enabled_infisical_seed_without_passwords(
        self,
    ):
        with patch.dict(
            "os.environ",
            {
                "TSW_SEED_INFISICAL_ITEMS": "1",
                "TSW_INFISICAL_LOGIN_EMAIL": "admin@example.com",
                "TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD": sample_text(
                    "master", "-value"
                ),
                "TSW_INFISICAL_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
                "TSW_INFISICAL_AUTH_SECRET": sample_text("auth", "-secret"),
                "TSW_INFISICAL_POSTGRES_PASSWORD": sample_text("pg", "-secret"),
                "TSW_INFISICAL_REDIS_PASSWORD": sample_text("redis", "-secret"),
                "TSW_PORTAINER_ADMIN_PASSWORD": sample_text("portainer", "-value"),
                "TSW_JENKINS_ADMIN_PASSWORD": sample_text("jenkins", "-value"),
                "TSW_POSTGRES_PASSWORD": sample_text("postgres", "-value"),
                "TSW_SONARQUBE_POSTGRES_PASSWORD": sample_text("sonar-pg", "-value"),
            },
            clear=True,
        ):
            with patch.object(composition, "ComposeFileRepositoryYaml"):
                with self.assertRaisesRegex(
                    ValueError,
                    "Required operator secret is missing: TSW_NEXUS_ADMIN_PASSWORD",
                ):
                    composition.build_lxc_deployment_services(
                        backend=composition.ManagedLxcBackend.INCUS,
                        service_profile=ServiceStackProfile.SERVICE_ACCESS,
                    )

    def test_build_setup_services_wires_phase_orchestrator_without_running_phases(self):
        with patch.object(
            composition,
            "_build_preflight_service_for_request",
        ) as build_preflight:
            with patch.object(composition, "build_platform_services") as build_platform:
                with patch.object(
                    composition,
                    "build_artifact_services_for_provider",
                ) as build_artifacts:
                    with patch.object(
                        composition,
                        "build_deployment_services_for_provider",
                    ) as build_deployment:
                        build_preflight.return_value = _phase_bundle()
                        build_platform.return_value = _platform_phase_bundle()
                        build_artifacts.return_value = _artifact_phase_bundle()
                        build_deployment.return_value = _deployment_phase_bundle()

                        with patch.object(
                            composition,
                            "_new_installation_trace_correlation_id",
                            return_value="trace-test",
                        ):
                            services = composition.build_setup_services(
                                _accepted_live_consent(),
                                allow_wsl_windows_filesystem=True,
                            )

        self.assertIsInstance(services.workflows.run, composition.SetupWorkflow)
        self.assertTrue(services.workflows.run.live_consent.accepted)
        self.assertIsInstance(
            services.workflows.run.progress,
            composition.CompositeWorkflowProgress,
        )
        self.assertIsInstance(
            services.workflows.run.method_trace,
            composition.CompositeMethodTrace,
        )
        self.assertEqual(services.workflows.run.trace_correlation_id, "trace-test")
        self.assertTrue(
            build_preflight.call_args.kwargs["allow_wsl_windows_filesystem"]
        )
        self.assertTrue(
            all(
                phase.method_trace is services.workflows.run.method_trace
                for phase in services.workflows.run.phases
            )
        )
        self.assertTrue(
            all(
                phase.trace_correlation_id
                == services.workflows.run.trace_correlation_id
                for phase in services.workflows.run.phases
            )
        )
        self.assertEqual(
            tuple(phase.name for phase in services.workflows.run.phases),
            (
                "preflight",
                "artifact contract preflight",
                "host prepare",
                "host verify",
                "platform init",
                "platform reconcile",
                "cluster docker",
                "cluster swarm bootstrap",
                "cluster verify",
                "platform expose",
                "deployment bootstrap",
                "artifact bootstrap",
                "artifact readiness gate",
                "artifacts prepare",
                "artifacts verify",
                "deployment apply",
                "deployment verify",
                "platform verify",
            ),
        )
        self.assertEqual(build_preflight.call_count, 1)
        self.assertEqual(
            ServiceStackProfile.SERVICE_ACCESS,
            build_preflight.call_args.args[0],
        )
        self.assertIsNone(build_preflight.call_args.args[1])
        self.assertIsNone(build_preflight.call_args.kwargs["configuration_validation"])
        self.assertIn("project_paths", build_preflight.call_args.kwargs)
        build_platform.assert_called_once_with(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
            live_consent=services.workflows.run.live_consent,
            ui=None,
            trace_correlation_id=services.workflows.run.trace_correlation_id,
            allow_wsl_windows_filesystem=True,
        )
        build_artifacts.assert_called_once_with(
            node_provider_request=None,
            ui=None,
            progress=services.workflows.run.progress,
        )
        build_deployment.assert_called_once_with(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
            node_provider_request=None,
            progress=services.workflows.run.progress,
        )
        build_preflight.return_value.run.assert_not_called()
        build_platform.return_value.workflows.init.run.assert_not_called()
        build_platform.return_value.workflows.expose.run.assert_not_called()
        build_artifacts.return_value.workflows.prepare.run.assert_not_called()
        build_deployment.return_value.workflows.apply.run.assert_not_called()

    def test_issue_252_remediation_wiring_shares_selected_incus_request(self):
        request = composition.NodeProviderSelectionRequest(
            requested_provider=composition.NodeProviderKind.LXC_NATIVE,
            preferred_backend=composition.ManagedLxcBackend.INCUS,
            backend_candidates=(composition.ManagedLxcBackend.INCUS,),
        )
        consent = _accepted_live_consent()

        with (
            patch.object(
                composition,
                "_build_preflight_service_for_request",
                return_value=_phase_bundle(),
            ) as build_preflight,
            patch.object(
                composition,
                "_build_artifact_readiness_gate",
                return_value=Mock(),
            ) as build_artifact_readiness,
            patch.object(
                composition,
                "build_host_preparation_service",
                return_value=Mock(),
            ) as build_host_preparation,
            patch.object(
                composition,
                "_build_platform_services_for_request",
                return_value=_platform_phase_bundle(),
            ) as build_platform,
            patch.object(
                composition,
                "build_artifact_services_for_provider",
                return_value=_artifact_phase_bundle(),
            ) as build_artifacts,
            patch.object(
                composition,
                "_build_deployment_services_for_request",
                return_value=_deployment_phase_bundle(),
            ) as build_deployment,
        ):
            services = composition.build_setup_services(
                consent,
                node_provider_request=request,
            )

        self.assertIsInstance(services.workflows.run, composition.SetupWorkflow)
        self.assertIs(request, build_preflight.call_args.args[1])
        self.assertIs(request, build_artifact_readiness.call_args.args[1])
        self.assertIs(request, build_platform.call_args.args[2])
        self.assertIs(
            request,
            build_artifacts.call_args.kwargs["node_provider_request"],
        )
        self.assertIs(
            request,
            build_deployment.call_args.kwargs["node_provider_request"],
        )
        build_host_preparation.assert_called_once_with(consent)

    def test_build_setup_services_passes_ui_to_platform_and_setup_terminal_sinks(self):
        live_consent = _accepted_live_consent()
        ui = _RecordingUI()
        captured: dict[str, object] = {}

        def build_platform(
            *,
            service_profile: object,
            live_consent: LiveConsent | None = None,
            ui: object | None = None,
            trace_correlation_id: str | None = None,
            allow_wsl_windows_filesystem: bool = False,
        ):
            captured["service_profile"] = service_profile
            captured["live_consent"] = live_consent
            captured["ui"] = ui
            captured["trace_correlation_id"] = trace_correlation_id
            captured["allow_wsl_windows_filesystem"] = allow_wsl_windows_filesystem
            return _platform_phase_bundle()

        def build_deployment(
            *,
            service_profile: object,
            node_provider_request: object | None = None,
            ui: object | None = None,
            progress: object | None = None,
        ):
            captured["deployment_service_profile"] = service_profile
            captured["deployment_node_provider_request"] = node_provider_request
            captured["deployment_ui"] = ui
            captured["deployment_progress"] = progress
            return _deployment_phase_bundle()

        with patch.object(
            composition, "build_preflight_service", return_value=_phase_bundle()
        ):
            with patch.object(
                composition, "build_platform_services", side_effect=build_platform
            ):
                with patch.object(
                    composition,
                    "build_artifact_services_for_provider",
                    return_value=_artifact_phase_bundle(),
                ):
                    with patch.object(
                        composition,
                        "build_deployment_services_for_provider",
                        side_effect=build_deployment,
                    ):
                        services = composition.build_setup_services(live_consent, ui=ui)

        progress_sink = services.workflows.run.progress
        method_trace_sink = services.workflows.run.method_trace
        self.assertIsInstance(progress_sink, composition.CompositeWorkflowProgress)
        self.assertIsInstance(method_trace_sink, composition.CompositeMethodTrace)
        progress_sinks = cast(
            composition.CompositeWorkflowProgress, progress_sink
        ).sinks
        method_trace_sinks = cast(
            composition.CompositeMethodTrace, method_trace_sink
        ).sinks

        self.assertIs(ui, captured["ui"])
        self.assertIs(ui, captured["deployment_ui"])
        self.assertIs(progress_sink, captured["deployment_progress"])
        self.assertIs(live_consent, captured["live_consent"])
        self.assertEqual(
            ServiceStackProfile.SERVICE_ACCESS, captured["deployment_service_profile"]
        )
        self.assertIsNone(captured["deployment_node_provider_request"])
        self.assertEqual(
            services.workflows.run.trace_correlation_id,
            captured["trace_correlation_id"],
        )
        self.assertTrue(
            any(
                isinstance(sink, composition.TerminalWorkflowProgress) and sink.ui is ui
                for sink in progress_sinks
            )
        )
        self.assertTrue(
            any(
                isinstance(sink, composition.TerminalMethodTrace) and sink.ui is ui
                for sink in method_trace_sinks
            )
        )

    def test_build_application_services_wires_preflight_through_platform_bundle(self):
        services = composition.build_application_services()

        self.assertIsInstance(services.platform.preflight, PreflightService)
        self.assertIs(services.preflight, services.platform.preflight)
        self.assertIsNot(
            services.platform.workflows.verify.steps[0],
            services.platform.preflight,
        )
        self.assertEqual(
            services.platform.workflows.verify.steps[0].configuration.required_ports,
            (),
        )

    def test_build_platform_services_wires_init_guard_when_live_consent_is_available(
        self,
    ):
        live_consent = _accepted_live_consent()
        services = composition.build_platform_services(live_consent=live_consent)

        self.assertIsNotNone(services.workflows.init.pre_apply_guard)
        self.assertTrue(services.lxc_node_provider.allow_live_mutation)
        self.assertTrue(services.lxc_docker_install.runtime.allow_live_mutation)
        self.assertTrue(services.lxc_proxy_drift_repair.runtime.allow_live_mutation)
        self.assertTrue(services.lxc_service_exposure.runtime.allow_live_mutation)
        self.assertTrue(services.lxc_swarm_bootstrap.swarm.allow_live_mutation)

    def test_lxc_docker_registry_mirror_configuration_uses_operator_environment(self):
        with patch.dict(
            os.environ,
            {
                "TSW_LXC_DOCKER_REGISTRY_MIRROR": sample_http_url(
                    ipv4_address(10, 0, 3, 1), 5001
                )
            },
            clear=True,
        ):
            with patch.object(
                composition.subprocess,
                "run",
                side_effect=AssertionError(
                    "explicit mirror configuration must not probe Docker"
                ),
            ):
                mirror = composition._lxc_docker_registry_mirror_configuration()

        self.assertIsNotNone(mirror)
        assert mirror is not None
        self.assertEqual(
            sample_http_url(ipv4_address(10, 0, 3, 1), 5001), mirror.mirror_url
        )
        self.assertEqual(mirror.registry_authority, f"{ipv4_address(10, 0, 3, 1)}:5001")

    def test_lxc_docker_registry_mirror_rejects_localhost_operator_value(self):
        with patch.dict(
            os.environ,
            {"TSW_LXC_DOCKER_REGISTRY_MIRROR": sample_http_url("127.0.0.1", 5001)},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                composition._lxc_docker_registry_mirror_configuration()

    def test_lxc_docker_registry_mirror_does_not_probe_without_operator_environment(
        self,
    ):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                composition.subprocess,
                "run",
                side_effect=AssertionError(
                    "unset mirror configuration must not probe Docker"
                ),
            ):
                mirror = composition._lxc_docker_registry_mirror_configuration()

        self.assertIsNone(mirror)

    def test_lxc_docker_apt_mirror_configuration_uses_operator_environment(self):
        host = ipv4_address(10, 0, 3, 1)
        with patch.dict(
            os.environ,
            {
                "TSW_LXC_UBUNTU_APT_MIRROR": sample_http_url(host, 8081)
                + "/repository/ubuntu-apt-proxy",
                "TSW_LXC_UBUNTU_SECURITY_APT_MIRROR": sample_http_url(host, 8081)
                + "/repository/ubuntu-security-apt-proxy",
                "TSW_LXC_DOCKER_APT_MIRROR": sample_http_url(host, 8081)
                + "/repository/docker-apt-proxy",
                "TSW_LXC_DOCKER_APT_GPG_URL": sample_http_url(host, 8081)
                + "/repository/docker-apt-proxy/gpg",
            },
            clear=True,
        ):
            mirror = composition._lxc_docker_apt_mirror_configuration()

        self.assertIsNotNone(mirror)
        assert mirror is not None
        self.assertEqual(
            sample_http_url(host, 8081) + "/repository/ubuntu-apt-proxy",
            mirror.ubuntu_archive_url,
        )
        self.assertEqual(
            sample_http_url(host, 8081) + "/repository/docker-apt-proxy",
            mirror.docker_apt_url,
        )
        self.assertTrue(mirror.configured)

    def test_lxc_docker_apt_mirror_configuration_returns_none_without_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            mirror = composition._lxc_docker_apt_mirror_configuration()

        self.assertIsNone(mirror)

    def test_lxc_backend_for_provider_request_honors_candidate_order(self):
        def which(name: str):
            return f"/usr/bin/{name}" if name == "incus" else None

        request = composition.NodeProviderSelectionRequest(
            backend_candidates=(composition.ManagedLxcBackend.INCUS,)
        )

        with patch.object(composition.shutil, "which", side_effect=which):
            backend = composition._lxc_backend_for_provider_request(request)

        self.assertEqual(composition.ManagedLxcBackend.INCUS, backend)

    def test_lxc_backend_for_provider_request_ignores_removed_lxd_candidate(self):
        def which(name: str):
            return f"/usr/bin/{name}" if name == "incus" else None

        request = composition.NodeProviderSelectionRequest(
            backend_candidates=(
                composition.ManagedLxcBackend.LXD,
                composition.ManagedLxcBackend.INCUS,
            )
        )

        with patch.object(composition.shutil, "which", side_effect=which):
            backend = composition._lxc_backend_for_provider_request(request)

        self.assertEqual(composition.ManagedLxcBackend.INCUS, backend)

    def test_preflight_configuration_for_incus_requires_incus_cli(self):
        request = composition.NodeProviderSelectionRequest(
            preferred_backend=composition.ManagedLxcBackend.INCUS,
        )

        configuration = composition._preflight_configuration_for_provider(
            composition.ServiceStackProfile.SERVICE_ACCESS,
            request,
        )

        dependency_names = {item.name for item in configuration.required_dependencies}
        self.assertIn("incus", dependency_names)
        self.assertNotIn("lxc", dependency_names)
        self.assertEqual(configuration.provider_metadata.provider, "lxc_native")
        self.assertEqual(configuration.provider_metadata.backend, "incus")
        self.assertIn(
            "selected-backend-control-network",
            configuration.provider_metadata.network_checks,
        )

    def test_infisical_readiness_steps_are_empty_for_default_profile(self):
        steps = composition._infisical_apply_readiness_steps(
            composition.ServiceStackProfile.DEFAULT,
            service_stack_by_name={},
        )

        self.assertEqual(steps, ())

    def test_preflight_configuration_honors_backend_candidate_order(self):
        def which(name: str):
            return f"/usr/bin/{name}" if name == "incus" else None

        request = composition.NodeProviderSelectionRequest(
            backend_candidates=(composition.ManagedLxcBackend.INCUS,)
        )

        with patch.object(composition.shutil, "which", side_effect=which):
            configuration = composition._preflight_configuration_for_provider(
                composition.ServiceStackProfile.SERVICE_ACCESS,
                request,
            )

        dependency_names = {item.name for item in configuration.required_dependencies}
        self.assertIn("incus", dependency_names)
        self.assertNotIn("lxc", dependency_names)
        self.assertEqual(configuration.provider_metadata.backend, "incus")

    def test_preflight_configuration_blocks_missing_lxc_backend_candidates(self):
        request = composition.NodeProviderSelectionRequest(backend_candidates=())

        with patch.object(composition.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "requires at least one"):
                composition._preflight_configuration_for_provider(
                    composition.ServiceStackProfile.SERVICE_ACCESS,
                    request,
                )

    def test_default_node_provider_request_uses_committed_candidate_order(self):
        request = composition._default_node_provider_request()

        self.assertEqual(composition.ManagedLxcBackend.INCUS, request.preferred_backend)
        self.assertEqual(
            request.backend_candidates,
            (composition.ManagedLxcBackend.INCUS,),
        )

    def test_build_setup_services_wires_live_consent_into_platform_init_guard(self):
        live_consent = _accepted_live_consent()
        captured: dict[str, object] = {}

        def build_platform(
            *,
            service_profile: object,
            live_consent: LiveConsent | None = None,
            ui: object | None = None,
            trace_correlation_id: str | None = None,
            allow_wsl_windows_filesystem: bool = False,
        ):
            captured["service_profile"] = service_profile
            captured["live_consent"] = live_consent
            captured["ui"] = ui
            captured["trace_correlation_id"] = trace_correlation_id
            captured["allow_wsl_windows_filesystem"] = allow_wsl_windows_filesystem
            return _platform_phase_bundle()

        with patch.object(
            composition, "build_preflight_service", return_value=_phase_bundle()
        ):
            with patch.object(
                composition, "build_platform_services", side_effect=build_platform
            ):
                with patch.object(
                    composition,
                    "build_artifact_services_for_provider",
                    return_value=_artifact_phase_bundle(),
                ):
                    with patch.object(
                        composition,
                        "build_deployment_services_for_provider",
                        return_value=_deployment_phase_bundle(),
                    ):
                        composition.build_setup_services(live_consent)

        self.assertIs(live_consent, captured["live_consent"])
        self.assertEqual(
            ServiceStackProfile.SERVICE_ACCESS, captured["service_profile"]
        )
        self.assertIsNone(captured["ui"])
        self.assertTrue(
            str(captured["trace_correlation_id"]).startswith("trace-installation-")
        )

    def test_build_application_services_does_not_run_constructed_services(self):
        services = composition.build_application_services()

        self.assertIsInstance(services, composition.ApplicationServices)

    def test_composed_default_lxc_init_workflow_blocks_before_live_step_execution(self):
        evidence_repository = _RecordingEvidenceRepository()
        blocked_result = VerificationResult(
            target_id="platform:node-provider:lxc_native",
            status=VerificationStatus.BLOCKED,
            message="Provider selection blocked node lifecycle before apply.",
            evidence={
                "phase": "pre_apply",
                "reason": "provider_selection_blocked",
            },
        )
        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                return_value=blocked_result,
            ):
                services = composition.build_platform_services()
                result = asyncio.run(services.workflows.init.run())

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(
            result.verification_results[0].target_id,
            "platform:node-provider:lxc_native",
        )
        self.assertEqual(
            result.verification_results[0].evidence["reason"],
            "provider_selection_blocked",
        )
        self.assertEqual(
            tuple(result.verification_results), evidence_repository.list_all()
        )

    def test_composed_default_lxc_cluster_workflows_run_runtime_and_swarm_steps(self):
        evidence_repository = _RecordingEvidenceRepository()

        async def verified_node(node, request=None):
            await async_checkpoint()
            return VerificationResult(
                target_id=f"platform:node:{node.name}",
                status=VerificationStatus.VERIFIED,
                message="Node lifecycle is verified.",
                evidence={"phase": "verify", "classification": "node_verified"},
            )

        async def verified_runtime(_service, _nodes):
            await async_checkpoint()
            return (
                VerificationResult(
                    target_id="container-runtime:swarm-manager",
                    status=VerificationStatus.VERIFIED,
                    message="Container runtime is verified.",
                    evidence={"phase": "verify"},
                ),
            )

        async def verified_swarm(_service, _manager, _workers):
            await async_checkpoint()
            return (
                VerificationResult(
                    target_id="swarm:swarm-manager",
                    status=VerificationStatus.VERIFIED,
                    message="Swarm manager is verified.",
                    evidence={"phase": "verify", "node": "swarm-manager"},
                ),
                VerificationResult(
                    target_id="swarm:swarm-worker-1",
                    status=VerificationStatus.VERIFIED,
                    message="Swarm worker is verified.",
                    evidence={"phase": "verify", "node": "swarm-worker-1"},
                ),
                VerificationResult(
                    target_id="swarm:swarm-worker-2",
                    status=VerificationStatus.VERIFIED,
                    message="Swarm worker is verified.",
                    evidence={"phase": "verify", "node": "swarm-worker-2"},
                ),
            )

        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                side_effect=verified_node,
            ):
                with patch.object(
                    composition.LxcDockerInstallService,
                    "ensure_docker_installed",
                    autospec=True,
                    side_effect=verified_runtime,
                ) as ensure_runtime:
                    with patch.object(
                        composition.LxcSwarmBootstrapService,
                        "bootstrap_swarm",
                        autospec=True,
                        side_effect=verified_swarm,
                    ) as bootstrap_swarm:
                        services = composition.build_platform_services()
                        init_result = asyncio.run(services.workflows.init.run())
                        docker_result = asyncio.run(
                            services.workflows.cluster.docker.run()
                        )
                        swarm_result = asyncio.run(
                            services.workflows.cluster.swarm_bootstrap.run()
                        )

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, init_result.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, docker_result.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, swarm_result.status)
        self.assertTrue(init_result.executed)
        self.assertEqual(
            tuple(item.target_id for item in init_result.verification_results),
            (
                "platform:node:swarm-manager",
                "platform:node:swarm-worker-1",
                "platform:node:swarm-worker-2",
            ),
        )
        self.assertEqual(
            tuple(item.target_id for item in docker_result.verification_results),
            ("platform:init:lxc-container-runtime",),
        )
        self.assertEqual(
            tuple(item.target_id for item in swarm_result.verification_results),
            ("platform:init:lxc-swarm-bootstrap",),
        )
        ensure_runtime.assert_called_once()
        bootstrap_swarm.assert_called_once()
        self.assertEqual(
            composition.DEFAULT_LXC_PLATFORM_NODES,
            ensure_runtime.call_args.args[1],
        )
        self.assertEqual(bootstrap_swarm.call_args.args[1].name, "swarm-manager")
        self.assertEqual(
            tuple(worker.name for worker in bootstrap_swarm.call_args.args[2]),
            ("swarm-worker-1", "swarm-worker-2"),
        )
        self.assertEqual(
            tuple(
                (*init_result.verification_results,
                 *docker_result.verification_results,
                 *swarm_result.verification_results)
            ),
            evidence_repository.list_all(),
        )

    def test_composed_default_lxc_init_without_live_consent_fails_closed_before_runtime_probe(
        self,
    ):
        evidence_repository = _RecordingEvidenceRepository()

        async def verified_node(node, request=None):
            await async_checkpoint()
            return VerificationResult(
                target_id=f"platform:node:{node.name}",
                status=VerificationStatus.VERIFIED,
                message="Node lifecycle is verified.",
                evidence={"phase": "verify", "classification": "node_verified"},
            )

        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                side_effect=verified_node,
            ):
                with patch.object(
                    composition,
                    "LxcContainerDockerRuntime",
                    side_effect=AssertionError(
                        "runtime adapter must not be constructed without consent"
                    ),
                ):
                    services = composition.build_platform_services()
                    result = asyncio.run(services.workflows.cluster.docker.run())

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(
            result.verification_results[-1].target_id,
            "platform:init:lxc-container-runtime",
        )
        self.assertEqual(
            result.verification_results[-1].evidence["classification"],
            "container_runtime_not_verified",
        )
        self.assertEqual(
            tuple(result.verification_results), evidence_repository.list_all()
        )

    def test_composed_default_lxc_reconcile_verifies_configured_nodes_without_provider_fallback(
        self,
    ):
        evidence_repository = _RecordingEvidenceRepository()

        async def verified_node(node, request=None):
            await async_checkpoint()
            return VerificationResult(
                target_id=f"platform:node:{node.name}",
                status=VerificationStatus.VERIFIED,
                message="Node already matches configured state.",
                evidence={
                    "phase": "verify",
                    "classification": "already_present",
                    "node": node.name,
                },
            )

        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                side_effect=verified_node,
            ) as ensure_node:
                with patch.object(
                    composition.CommandWorkflow,
                    "verify_config_contract",
                    side_effect=AssertionError(
                        "default reconcile must not inspect command contracts"
                    ),
                ) as verify_config_contract:
                    services = composition.build_platform_services()
                    result = asyncio.run(services.workflows.reconcile.run())

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertTrue(result.executed)
        verify_config_contract.assert_not_called()
        self.assertEqual(
            tuple(
                f"platform:node:{node.name}"
                for node in composition.DEFAULT_LXC_PLATFORM_NODES
            ),
            tuple(item.target_id for item in result.verification_results),
        )
        self.assertEqual(
            [call.args[0].name for call in ensure_node.call_args_list],
            ["swarm-manager", "swarm-worker-1", "swarm-worker-2"],
        )
        self.assertEqual(
            tuple(result.verification_results), evidence_repository.list_all()
        )

    def test_composed_default_lxc_reconcile_reports_converged_node_drift(self):
        evidence_repository = _RecordingEvidenceRepository()

        async def reconcile_node(node, request=None):
            await async_checkpoint()
            applied = node.name == "swarm-worker-1"
            evidence = {
                "phase": "apply" if applied else "verify",
                "classification": "started" if applied else "already_present",
                "node": node.name,
            }
            if applied:
                evidence["applied"] = "true"
            return VerificationResult(
                target_id=f"platform:node:{node.name}",
                status=VerificationStatus.VERIFIED,
                message="Node lifecycle is reconciled.",
                evidence=evidence,
            )

        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                side_effect=reconcile_node,
            ):
                services = composition.build_platform_services()
                result = asyncio.run(services.workflows.reconcile.run())

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(
            result.to_dict()["outcome"]["mutation"]["result"],
            "converged",
        )
        self.assertEqual(
            next(
                item
                for item in result.verification_results
                if item.evidence.get("applied") == "true"
            ).target_id,
            "platform:node:swarm-worker-1",
        )
        self.assertEqual(
            tuple(result.verification_results), evidence_repository.list_all()
        )

    def test_composed_default_lxc_reconcile_blocks_before_unapproved_mutation(self):
        evidence_repository = _RecordingEvidenceRepository()

        async def blocked_node(node, request=None):
            await async_checkpoint()
            return VerificationResult(
                target_id=f"platform:node:{node.name}",
                status=VerificationStatus.BLOCKED,
                message="Live mutation is required to reconcile node drift.",
                evidence={
                    "phase": "pre_apply",
                    "reason": "live_mutation_required",
                    "node": node.name,
                },
            )

        with patch.object(
            composition,
            "VerificationEvidenceLocalRepository",
            return_value=evidence_repository,
        ):
            with patch.object(
                composition.NodeProviderSelectionService,
                "ensure_node",
                side_effect=blocked_node,
            ):
                services = composition.build_platform_services()
                result = asyncio.run(services.workflows.reconcile.run())

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(
            result.to_dict()["outcome"]["mutation"]["result"],
            "blocked",
        )
        self.assertEqual(
            result.verification_results[0].target_id,
            "platform:node:swarm-manager",
        )
        self.assertEqual(
            tuple(result.verification_results), evidence_repository.list_all()
        )

    def test_composed_default_lxc_expose_uses_manager_gateway_and_setup_ports(self):
        services = composition.build_platform_services()

        self.assertEqual(len(services.workflows.expose.steps), 2)
        step = services.workflows.expose.steps[0]
        socat_step = services.workflows.expose.steps[1]

        self.assertIsInstance(step, composition.LxcServiceExposureStep)
        self.assertIsInstance(socat_step, composition._WslSocatExposeStep)
        self.assertIs(step.service, services.lxc_service_exposure)
        self.assertIs(socat_step.socat_manager, services.socat_manager)
        self.assertIsInstance(
            socat_step.socat_exposure,
            composition.WslSocatExposureAdapter,
        )
        self.assertEqual(step.service.gateway_node.name, "swarm-manager")
        self.assertEqual(
            composition.DEFAULT_LXC_MANAGER_PROXY_PROFILE,
            step.service.manager_profile_name,
        )
        self.assertEqual(
            composition.DEFAULT_LXC_PROXY_LISTEN_ADDRESS,
            step.service.listen_address,
        )
        self.assertEqual(len(step.service.setup_manifest.required_ports), 18)
        self.assertEqual(step.service.setup_manifest.services[-1].name, "Infisical")

    def test_composed_wsl_socat_expose_verifies_not_required_on_native_linux(self):
        services = composition.build_platform_services()
        socat_step = services.workflows.expose.steps[1]
        socat_step.os_type = composition.OsTypes.LINUX

        result = asyncio.run(socat_step.run())

        self.assertEqual(VerificationStatus.VERIFIED, result.status)
        self.assertEqual(result.evidence["classification"], "not_required")

    def test_composed_wsl_socat_expose_blocks_without_live_consent_before_adapter(self):
        services = composition.build_platform_services()
        socat_step = services.workflows.expose.steps[1]
        socat_step.os_type = composition.OsTypes.WSL_LINUX

        with patch.object(
            socat_step.socat_exposure,
            "is_available",
            new=AsyncMock(side_effect=AssertionError("consent guard must run first")),
        ):
            result = asyncio.run(socat_step.run())

        self.assertEqual(VerificationStatus.BLOCKED, result.status)
        self.assertEqual(
            result.evidence["classification"],
            "live_mutation_required",
        )
        self.assertEqual(result.evidence["planned_forward_count"], "18")

    def test_composed_wsl_socat_expose_skips_missing_optional_socat(self):
        with patch.object(wsl_socat_exposure.shutil, "which", return_value=None):
            services = composition.build_platform_services(
                live_consent=LiveConsent(live_flag=True, confirmed=True)
            )
            socat_step = services.workflows.expose.steps[1]
            socat_step.os_type = composition.OsTypes.WSL_LINUX
            result = asyncio.run(socat_step.run())

        self.assertEqual(VerificationStatus.VERIFIED, result.status)
        self.assertEqual(result.evidence["classification"], "socat_missing_skipped")
        self.assertEqual(result.evidence["planned_forward_count"], "18")

    def test_composed_lxc_proxy_drift_repair_uses_manager_profile_scope(self):
        services = composition.build_platform_services()

        self.assertEqual(len(services.workflows.repair_lxc_proxy_drift.steps), 1)
        step = services.workflows.repair_lxc_proxy_drift.steps[0]

        self.assertIsInstance(step, composition.LxcProxyDriftRepairStep)
        self.assertIs(step.service, services.lxc_proxy_drift_repair)
        self.assertEqual(step.service.gateway_node.name, "swarm-manager")
        self.assertEqual(
            composition.DEFAULT_LXC_MANAGER_PROXY_PROFILE,
            step.service.manager_profile_name,
        )
        self.assertEqual(
            composition.DEFAULT_LXC_PROXY_LISTEN_ADDRESS,
            step.service.listen_address,
        )
        self.assertEqual(len(step.service.setup_manifest.required_ports), 18)

    def test_composed_default_lxc_expose_without_live_consent_fails_closed(self):
        with patch.object(
            composition,
            "LxcProxyDeviceRuntime",
            side_effect=AssertionError("proxy runtime must not run without consent"),
        ):
            services = composition.build_platform_services()
            result = asyncio.run(services.workflows.expose.run())

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, result.status)
        self.assertEqual(
            result.verification_results[0].target_id,
            "platform:expose:lxc-proxy-devices",
        )
        self.assertEqual(
            result.verification_results[0].evidence["lookup_failure_count"],
            "18",
        )


def _blocked_contract_result(target_id: str) -> VerificationResult:
    return VerificationResult(
        target_id=target_id,
        status=VerificationStatus.BLOCKED,
        message="Command-backed verification is not configured.",
        evidence={
            "phase": "pre_apply",
            "reason": "command_backed_verification_missing",
        },
    )


def _accepted_live_consent() -> LiveConsent:
    return LiveConsent(
        live_flag=True,
        environment_value=LIVE_CONSENT_ENVIRONMENT_VALUE,
        typed_phrase=LIVE_CONSENT_PHRASE,
    )


    def test_setup_max_concurrency_operator_config_is_positive_and_configurable(self):
        with patch.dict("os.environ", {"TSW_SETUP_MAX_CONCURRENCY": "3"}):
            self.assertEqual(
                composition._operator_config_int(
                    "TSW_SETUP_MAX_CONCURRENCY",
                    2,
                    minimum=1,
                ),
                3,
            )
        with patch.dict("os.environ", {"TSW_SETUP_MAX_CONCURRENCY": "0"}):
            with self.assertRaisesRegex(ValueError, "at least 1"):
                composition._operator_config_int(
                    "TSW_SETUP_MAX_CONCURRENCY",
                    2,
                    minimum=1,
                )


class _RecordingEvidenceRepository:
    def __init__(self) -> None:
        self.results: list[VerificationResult] = []

    def append(self, result: VerificationResult) -> None:
        self.results.append(result)

    def list_all(self) -> tuple[VerificationResult, ...]:
        return tuple(self.results)


class _ExistingPath:
    def __init__(self, *, exists: bool):
        self._exists = exists

    def exists(self):
        return self._exists


class _RecordingUI(PortUI):
    def __init__(self):
        super().__init__(instances=(), test_mode=True)

    def start(self):
        return None


class _LifecycleRecordingUI(PortUI):
    def __init__(self, calls: list[str]):
        super().__init__(instances=(), test_mode=True)
        self.calls = calls
        self.updates: list[tuple[str, str, str, str | None]] = []

    def start_in_thread(self):
        self.calls.append("ui started")
        self.ui_thread = _record_ui_awaited(self.calls)

    def update_status(self, instance, task, step, result=None):
        super().update_status(instance, task, step, result)
        status = self._status_for_instance(instance)
        self.updates.append((instance, task, step, status["result"]))
        if instance == AGGREGATE_INSTANCE and step in {"finished", "exception"}:
            self.calls.append(f"ui update {status['result']}")

    def start(self):
        return None


async def _record_ui_awaited(calls: list[str]):
    await async_checkpoint()
    calls.append("ui awaited")


def _phase_bundle():
    from unittest.mock import AsyncMock

    return type("PhaseBundle", (), {"run": AsyncMock()})()


def _workflow_bundle(*names: str):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    return SimpleNamespace(
        workflows=SimpleNamespace(
            **{name: SimpleNamespace(run=AsyncMock()) for name in names}
        )
    )


def _platform_phase_bundle():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    return SimpleNamespace(
        workflows=SimpleNamespace(
            init=SimpleNamespace(run=AsyncMock()),
            reconcile=SimpleNamespace(run=AsyncMock()),
            cluster=SimpleNamespace(
                docker=SimpleNamespace(run=AsyncMock()),
                swarm_bootstrap=SimpleNamespace(run=AsyncMock()),
                verify=SimpleNamespace(run=AsyncMock()),
            ),
            expose=SimpleNamespace(run=AsyncMock()),
            verify=SimpleNamespace(run=AsyncMock()),
        )
    )


def _artifact_phase_bundle():
    return _workflow_bundle("prepare", "verify")


def _deployment_phase_bundle():
    return _workflow_bundle("bootstrap", "apply", "verify")


class _FakeEndpointResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeEndpointSession:
    def __init__(self, responses: tuple[object, ...]):
        self.responses = list(responses)
        self.requests: list[tuple[str, int, bool]] = []

    def get(self, url: str, *, timeout: int, allow_redirects: bool):
        self.requests.append((url, timeout, allow_redirects))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return _FakeEndpointResponse(cast(int, response))


def _setup_lifecycle_bundle(
    calls: list[str],
    result: SetupWorkflowResult | Exception,
    *,
    ui: PortUI | None = None,
    status_updates: tuple[str, ...] = (),
):
    from types import SimpleNamespace

    class SetupRun:
        async def run(self):
            await async_checkpoint()
            calls.append("workflow run")
            if ui is not None:
                for status in status_updates:
                    ui.update_status(
                        AGGREGATE_INSTANCE,
                        task="setup run",
                        step="workflow progress",
                        result=status,
                    )
            if isinstance(result, Exception):
                raise result
            return result

    return SimpleNamespace(workflows=SimpleNamespace(run=SetupRun()))


def _setup_result(status: SetupWorkflowStatus) -> SetupWorkflowResult:
    return SetupWorkflowResult(
        kind=SetupWorkflowKind.RUN,
        status=status,
        message=f"setup run {status.value}.",
        reason=status.value,
        executed=True,
    )
