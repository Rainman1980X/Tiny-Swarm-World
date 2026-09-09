import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import requests
from tests.support.sonar_safe_literals import (
    ipv4_address,
    operator_credential,
    sample_http_url,
    sensitive_assignment,
)

from tiny_swarm_world.application.ports.clients.port_portainer_admin_client import (
    PortainerAdminInitializationRejected,
)
from tiny_swarm_world.domain.deployment.stack_definition import StackDefinition
from tiny_swarm_world.domain.node_provider import ManagedLxcBackend
from tiny_swarm_world.domain.ingress import ResolvedTlsContract, TlsAuthorityMode
from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
    ImagePublisherOperationRejected,
    LxcContainerRuntime,
    LxcContainerImagePublisher,
    LxcNexusHttpClient,
    LxcPortainerAdminClient,
    LxcSwarmRuntime as _ProductionLxcSwarmRuntime,
    PublicImagePullRejected,
    _external_overlay_network_names,
    _lxc_manager_ip,
    _published_ports_from_json,
    _safe_log_text,
)
from tiny_swarm_world.domain.artifacts import ContainerImageContract
from tiny_swarm_world.infrastructure.project_paths import ProjectPaths


class _FakeTlsResolver:
    def __init__(self):
        self._temporary = TemporaryDirectory()
        root = Path(self._temporary.name)
        self.ca = root / "ca.crt"
        self.certificate = root / "tls.crt"
        self.key = root / "tls.key"
        self.ca.write_bytes(b"ca")
        self.certificate.write_bytes(b"certificate")
        self.key.write_bytes(b"private-key")

    def resolve(self):
        return ResolvedTlsContract(
            mode=TlsAuthorityMode.EXTERNAL,
            ca_certificate=self.ca,
            leaf_certificate=self.certificate,
            leaf_private_key=self.key,
            trust_bundle=self.ca,
            certificate_secret_name="custom_tls_cert",
            private_key_secret_name="custom_tls_key",
            lifecycle_fingerprint="0" * 64,
            certificate_bytes=b"certificate",
            private_key_bytes=b"private-key",
        )

    def close(self):
        self._temporary.cleanup()


def LxcSwarmRuntime(**kwargs):
    kwargs.setdefault("tls_contract_resolver", Mock())
    return _ProductionLxcSwarmRuntime(**kwargs)


class TestLxcSwarmRuntime(unittest.TestCase):
    def test_deploy_stack_uses_lxc_exec_manager_shell(self):
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            remote_stack_root="/custom/stacks",
        )

        with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
            with patch.object(runtime, "_transfer_stack_assets") as transfer_stack_assets:
                runtime.deploy_stack(
                    StackDefinition(name="swagger", compose_content="services: {}")
                )

        transfer_stack_assets.assert_called_once_with("swagger", "/custom/stacks/swagger")
        deploy_script = run_manager_shell.call_args_list[-1].args[0]
        self.assertIn("TSW_REMOTE_STACK_ROOT=/custom/stacks docker stack deploy", deploy_script)
        self.assertIn("--resolve-image never", deploy_script)
        self.assertIn("--with-registry-auth", deploy_script)
        self.assertIn("-c /custom/stacks/swagger/docker-compose.yml swagger", deploy_script)
        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertFalse(any(script.startswith("docker service inspect") for script in scripts))
        self.assertFalse(any(script.startswith("docker service update") for script in scripts))

    def test_deploy_stack_writes_generated_service_access_dashboard_before_stack_deploy(self):
        generated_dashboard = "<!doctype html>\n<html><body>generated-dashboard</body></html>\n"
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            remote_stack_root="/custom/stacks",
            service_access_dashboard_renderer=lambda: generated_dashboard,
        )

        with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
            runtime.deploy_stack(
                StackDefinition(name="service-access", compose_content="services: {}")
            )

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertEqual(len(scripts), 3)
        self.assertIn("cat > /custom/stacks/service-access/docker-compose.yml", scripts[0])
        self.assertIn(
            "cat > /custom/stacks/service-access/dashboard/index.html",
            scripts[1],
        )
        self.assertIn("docker stack deploy", scripts[2])
        self.assertEqual(
            run_manager_shell.call_args_list[1].kwargs["input_text"],
            generated_dashboard,
        )

    def test_portainer_deploy_provisions_admin_password_as_external_secret(self):
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            portainer_admin_password=operator_credential(),
        )

        with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
            runtime.deploy_stack(
                StackDefinition(name="portainer", compose_content="services: {}")
            )

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertIn(
            "docker secret inspect -- tsw_portainer_admin_password >/dev/null 2>&1",
            scripts,
        )
        self.assertIn(
            "docker secret create -- tsw_portainer_admin_password -",
            scripts,
        )
        create_call = next(
            call
            for call in run_manager_shell.call_args_list
            if "docker secret create -- tsw_portainer_admin_password -" in call.args[0]
        )
        self.assertEqual(create_call.kwargs["input_text"], operator_credential())
        self.assertNotIn(operator_credential(), scripts[0])

    def test_default_remote_stack_root_matches_committed_compose_fallback(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        self.assertEqual(runtime.remote_stack_root, "/var/lib/tiny-swarm-world/stacks")

    def test_prepare_stack_assets_transfers_swagger_assets_to_remote_root(self):
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            remote_stack_root="/custom/stacks",
        )

        with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
            runtime.prepare_stack_assets("swagger")

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertIn("mkdir -p /custom/stacks/swagger/swagger", scripts[0])
        self.assertIn("cat > /custom/stacks/swagger/swagger/openapi.json", scripts[0])
        self.assertIn("mkdir -p /custom/stacks/swagger/nginx", scripts[1])
        self.assertIn("cat > /custom/stacks/swagger/nginx/default.conf", scripts[1])

    def test_prepare_stack_assets_transfers_traefik_dynamic_tls_config(self):
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            remote_stack_root="/custom/stacks",
        )

        with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
            runtime.prepare_stack_assets("traefik")

        script = run_manager_shell.call_args.args[0]
        input_text = run_manager_shell.call_args.kwargs["input_text"]
        self.assertIn("mkdir -p /custom/stacks/traefik/dynamic", script)
        self.assertIn("cat > /custom/stacks/traefik/dynamic/tls.yml", script)
        self.assertIn("/run/secrets/tsw_traefik_tls_cert", input_text)
        self.assertIn("/run/secrets/tsw_traefik_tls_key", input_text)

    def test_prepare_stack_assets_transfers_generated_service_access_dashboard_to_remote_root(self):
        with TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory)
            dashboard_file = (
                repository_root
                / "infra"
                / "config"
                / "compose"
                / "service-access"
                / "dashboard"
                / "index.html"
            )
            dashboard_file.parent.mkdir(parents=True)
            dashboard_file.write_text("<html>stale-dashboard</html>", encoding="utf-8")
            project_paths = ProjectPaths.from_roots(repository_root)
            generated_dashboard = "<!doctype html>\n<html><body>generated-dashboard</body></html>\n"
            runtime = LxcSwarmRuntime(
                backend=ManagedLxcBackend.LXD,
                remote_stack_root="/custom/stacks",
                project_paths=project_paths,
            )
            setattr(
                runtime,
                "service_access_dashboard_renderer",
                lambda: generated_dashboard,
            )

            with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
                runtime.prepare_stack_assets("service-access")

        script = run_manager_shell.call_args.args[0]
        input_text = run_manager_shell.call_args.kwargs["input_text"]
        self.assertIn("mkdir -p /custom/stacks/service-access/dashboard", script)
        self.assertIn("cat > /custom/stacks/service-access/dashboard/index.html", script)
        self.assertEqual(input_text, generated_dashboard)
        self.assertNotIn("stale-dashboard", input_text)

    def test_render_service_access_dashboard_falls_back_to_compose_repository(self):
        with TemporaryDirectory() as temporary_directory:
            project_paths = ProjectPaths.from_roots(Path(temporary_directory))
            runtime = LxcSwarmRuntime(
                backend=ManagedLxcBackend.LXD,
                project_paths=project_paths,
            )

            with patch(
                "tiny_swarm_world.infrastructure.adapters.repositories."
                "compose_file_repository_yaml.ComposeFileRepositoryYaml"
            ) as compose_repository:
                compose_repository.return_value.render_service_access_dashboard.return_value = (
                    "<html>generated-dashboard</html>"
                )

                dashboard_html = runtime._render_service_access_dashboard()

        self.assertEqual(dashboard_html, "<html>generated-dashboard</html>")
        compose_repository.assert_called_once_with(project_paths=project_paths)
        compose_repository.return_value.render_service_access_dashboard.assert_called_once_with()

    def test_traefik_tls_secret_generation_covers_local_ingress_hostnames(self):
        tls_resolver = _FakeTlsResolver()
        self.addCleanup(tls_resolver.close)
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.LXD,
            traefik_tls_cert_secret_name="custom_tls_cert",
            traefik_tls_key_secret_name="custom_tls_key",
            tls_contract_resolver=tls_resolver,
        )
        tls_resolver.certificate.write_bytes(b"replacement-certificate")
        tls_resolver.key.write_bytes(b"replacement-private-key")

        with patch.object(
            runtime,
            "external_secret_exists",
            side_effect=(False, False, True, True),
        ):
            owned_labels = "tiny-swarm-world|" + "0" * 64 + "\n"
            with patch.object(
                runtime,
                "_run_manager_shell",
                side_effect=(
                    subprocess.CompletedProcess([], 0, stdout="idcert|idkey\n"),
                    subprocess.CompletedProcess([], 0, stdout=owned_labels),
                    subprocess.CompletedProcess([], 0, stdout=owned_labels),
                ),
            ) as run_manager_shell:
                runtime._ensure_traefik_tls_secrets()

        reconciliation_call = run_manager_shell.call_args_list[0]
        script = reconciliation_call.args[0]
        self.assertIn("base64 -d", script)
        self.assertIn("custom_tls_cert", script)
        self.assertIn("custom_tls_key", script)
        self.assertIn("umask 077", script)
        self.assertIn("chmod 600", script)
        self.assertEqual(
            reconciliation_call.kwargs["input_text"],
            "Y2VydGlmaWNhdGU=\ncHJpdmF0ZS1rZXk=\n",
        )
        self.assertNotIn("private-key", script)
        self.assertNotIn("certificate", script)

    def test_reconcile_published_ports_preserves_declared_host_mode(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)
        compose = """
services:
  nexus:
    image: sonatype/nexus3:3.75.1
    ports:
      - target: 8081
        published: 8081
        protocol: tcp
        mode: host
"""

        with patch.object(
            runtime,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess([], 0, stdout="[]"),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            runtime._reconcile_host_published_ports(StackDefinition(name="nexus", compose_content=compose))

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertIn(
            "docker service update --publish-add published=8081,target=8081,protocol=tcp,mode=host nexus_nexus",
            scripts,
        )

    def test_reconcile_published_ports_reconciles_ingress_back_to_host_mode(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)
        compose = """
services:
  nexus:
    image: sonatype/nexus3:3.75.1
    ports:
      - target: 8081
        published: 8081
        protocol: tcp
        mode: host
"""

        with patch.object(
            runtime,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout=(
                        '[{"Protocol":"tcp","TargetPort":8081,'
                        '"PublishedPort":8081,"PublishMode":"ingress"}]'
                    ),
                ),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            runtime._reconcile_host_published_ports(StackDefinition(name="nexus", compose_content=compose))

        update_scripts = [
            call.args[0]
            for call in run_manager_shell.call_args_list
            if call.args[0].startswith("docker service update")
        ]
        self.assertEqual(len(update_scripts), 1)
        self.assertIn(
            "--publish-rm published=8081,target=8081,protocol=tcp,mode=ingress",
            update_scripts[0],
        )
        self.assertIn(
            "--publish-add published=8081,target=8081,protocol=tcp,mode=host",
            update_scripts[0],
        )

    def test_reconcile_published_ports_keeps_manager_constrained_ports_in_host_mode(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)
        compose = """
services:
  portainer:
    image: portainer/portainer-ce:2.39.2
    ports:
      - target: 9000
        published: 9000
        protocol: tcp
        mode: host
    deploy:
      placement:
        constraints:
          - node.role == manager
"""

        with patch.object(
            runtime,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess([], 0, stdout="[]"),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            runtime._reconcile_host_published_ports(
                StackDefinition(name="portainer", compose_content=compose)
            )

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertIn(
            "docker service update --publish-add published=9000,target=9000,protocol=tcp,mode=host portainer_portainer",
            scripts,
        )

    def test_reconcile_published_ports_adds_only_missing_manager_constrained_ports(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)
        compose = """
services:
  service-access-nginx:
    image: nginx:mainline-alpine
    ports:
      - target: 80
        published: 10000
        protocol: tcp
        mode: host
      - target: 8086
        published: 8086
        protocol: tcp
        mode: host
    deploy:
      placement:
        constraints:
          - node.role == manager
"""

        with patch.object(
            runtime,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess(
                    [],
                    0,
                    stdout=(
                        '[{"Protocol":"tcp","TargetPort":80,'
                        '"PublishedPort":10000,"PublishMode":"host"}]'
                    ),
                ),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            runtime._reconcile_host_published_ports(
                StackDefinition(name="service-access", compose_content=compose)
            )

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        update_scripts = [script for script in scripts if script.startswith("docker service update")]
        self.assertEqual(len(update_scripts), 1)
        self.assertIn(
            "--publish-add published=8086,target=8086,protocol=tcp,mode=host",
            update_scripts[0],
        )
        self.assertNotIn("published=10000,target=80", update_scripts[0])

    def test_deploy_stack_creates_missing_external_overlay_networks_idempotently(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)
        compose = """
services:
  nginx:
    image: nginx:mainline-alpine
    networks:
      - service_access_link
networks:
  service_access_link:
    name: service_access_link
    external: true
"""
        inspect_missing = subprocess.CompletedProcess([], 1)
        success = subprocess.CompletedProcess([], 0)

        with patch.object(
            runtime,
            "_run_manager_shell",
            side_effect=(inspect_missing, success, success, success),
        ) as run_manager_shell:
            with patch.object(runtime, "_transfer_stack_assets"):
                runtime.deploy_stack(StackDefinition(name="service-access", compose_content=compose))

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertIn(
            "docker network inspect -- service_access_link >/dev/null 2>&1",
            scripts,
        )
        self.assertIn(
            "docker network create --driver overlay --attachable -- service_access_link >/dev/null",
            scripts,
        )

    def test_external_overlay_network_names_uses_explicit_shared_name(self):
        compose = """
networks:
  local_only: {}
  service_access_link:
    name: service_access_link
    external: true
  alternate:
    external: true
"""

        self.assertEqual(
            _external_overlay_network_names(
                StackDefinition(name="service-access", compose_content=compose)
            ),
            ("service_access_link", "alternate"),
        )

    def test_published_ports_from_json_parses_docker_endpoint_ports(self):
        self.assertEqual(
            _published_ports_from_json(
                """
[
  {"Protocol": "tcp", "TargetPort": 80, "PublishedPort": 10000, "PublishMode": "host"},
  {"Protocol": "tcp", "TargetPort": 8086, "PublishedPort": 8086, "PublishMode": "host"}
]
"""
            ),
            {("10000", "80", "tcp", "host"), ("8086", "8086", "tcp", "host")},
        )

    def test_stack_exists_reads_docker_stack_names_through_lxc(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(
            runtime,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0, stdout="portainer\nnexus\n"),
        ) as run_manager_shell:
            self.assertTrue(runtime.stack_exists("nexus"))

        run_manager_shell.assert_called_once_with(
            "docker stack ls --format '{{.Name}}'",
            check=False,
        )

    def test_infisical_migration_lock_recovery_unlocks_only_known_lock_table(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with (
            patch.object(
                runtime,
                "_run_manager_shell",
                return_value=subprocess.CompletedProcess(
                    [],
                    0,
                    stdout="swarm-worker-1\n",
                ),
            ) as run_manager_shell,
            patch.object(
                runtime,
                "_run_node_shell",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run_node_shell,
        ):
            self.assertTrue(runtime.recover_infisical_migration_lock())

        script = run_node_shell.call_args.args[1]
        self.assertIn(
            "--filter label=com.docker.swarm.service.name=infisical_infisical-db",
            script,
        )
        self.assertIn("wc -l", script)
        self.assertIn("for lock_table in infisical_migrations_lock", script)
        self.assertIn("to_regclass('public.' || '$lock_table')", script)
        self.assertIn("infisical_migrations_startup_lock", script)
        self.assertIn("update $lock_table set is_locked=0", script)
        self.assertIn("where is_locked<>0", script)
        run_manager_shell.assert_called_once_with(
            "docker service ps --filter desired-state=running "
            "--format '{{.Node}}' infisical_infisical-db",
            check=False,
        )

    def test_infisical_migration_lock_recovery_runs_on_the_db_task_node(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with (
            patch.object(
                runtime,
                "_run_manager_shell",
                return_value=subprocess.CompletedProcess(
                    [],
                    0,
                    stdout="swarm-worker-1\n",
                ),
            ) as run_manager_shell,
            patch.object(
                runtime,
                "_run_node_shell",
                return_value=subprocess.CompletedProcess([], 0),
            ) as run_node_shell,
        ):
            self.assertTrue(runtime.recover_infisical_migration_lock())

        placement_script = run_manager_shell.call_args.args[0]
        self.assertIn("docker service ps", placement_script)
        self.assertIn("infisical_infisical-db", placement_script)
        recovery_script = run_node_shell.call_args.args[1]
        self.assertIn(
            "--filter label=com.docker.swarm.service.name=infisical_infisical-db",
            recovery_script,
        )
        self.assertIn("for lock_table in infisical_migrations_lock", recovery_script)
        run_node_shell.assert_called_once_with(
            "swarm-worker-1",
            recovery_script,
            check=False,
        )

    def test_infisical_migration_lock_recovery_rejects_ambiguous_task_placement(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with (
            patch.object(
                runtime,
                "_run_manager_shell",
                return_value=subprocess.CompletedProcess(
                    [],
                    0,
                    stdout="swarm-worker-1\nswarm-worker-2\n",
                ),
            ),
            patch.object(runtime, "_run_node_shell") as run_node_shell,
        ):
            self.assertFalse(runtime.recover_infisical_migration_lock())

        run_node_shell.assert_not_called()

    def test_node_shell_timeout_identifies_the_target_worker(self):
        runtime = LxcSwarmRuntime(
            backend=ManagedLxcBackend.INCUS,
            timeout_seconds=1,
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["incus", "exec"], 1),
        ):
            with self.assertRaisesRegex(RuntimeError, "swarm-worker-1"):
                runtime._run_node_shell("swarm-worker-1", "true")

    def test_list_stack_services_parses_replica_counts(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(
            runtime,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess(
                [],
                0,
                stdout="service-access_vaultwarden|1/1\nservice-access_nginx|0/1\n",
            ),
        ) as run_manager_shell:
            services = runtime.list_stack_services("service-access")

        self.assertEqual(
            tuple(service.service_name for service in services),
            ("service-access_vaultwarden", "service-access_nginx"),
        )
        self.assertEqual(tuple(service.current_replicas for service in services), (1, 0))
        self.assertEqual(tuple(service.desired_replicas for service in services), (1, 1))
        run_manager_shell.assert_called_once_with(
            "timeout --kill-after=5s 30s docker service ls "
            "--filter label=com.docker.stack.namespace=service-access "
            "--format '{{.Name}}|{{.Replicas}}'",
            check=False,
            timeout_seconds=runtime.service_list_timeout_seconds + 10,
        )

    def test_list_stack_services_filters_by_stack_namespace_label(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(
            runtime,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess(
                [],
                0,
                stdout="pulsar_pulsar|1/1\npulsar_pulsar-manager|0/1\n",
            ),
        ) as run_manager_shell:
            services = runtime.list_stack_services("pulsar")

        self.assertEqual(
            tuple(service.service_name for service in services),
            ("pulsar_pulsar", "pulsar_pulsar-manager"),
        )
        self.assertEqual(tuple(service.current_replicas for service in services), (1, 0))
        self.assertEqual(tuple(service.desired_replicas for service in services), (1, 1))
        run_manager_shell.assert_called_once_with(
            "timeout --kill-after=5s 30s docker service ls "
            "--filter label=com.docker.stack.namespace=pulsar "
            "--format '{{.Name}}|{{.Replicas}}'",
            check=False,
            timeout_seconds=runtime.service_list_timeout_seconds + 10,
        )

    def test_safe_log_text_redacts_secret_like_assignments(self):
        text = _safe_log_text(
            "TSW_PULSAR_ADMIN_TOKEN=header.payload.signature "
            "TSW_NEXUS_ADMIN_PASSWORD='operator-value' "
            "authParams=token:header.payload.signature "
            "Authorization: Bearer header.payload.signature"
        )

        self.assertNotIn("header.payload.signature", text)
        self.assertNotIn("operator-value", text)
        self.assertIn("TSW_PULSAR_ADMIN_TOKEN=***", text)
        self.assertIn("TSW_NEXUS_ADMIN_PASSWORD=***", text)
        self.assertIn("authParams=token:***", text)

    def test_run_manager_shell_retries_transient_incus_child_pid_failure(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.INCUS)
        transient_failure = subprocess.CompletedProcess(
            [],
            255,
            stdout="",
            stderr="Error: Failed to retrieve PID of executing child process",
        )
        success = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.time.sleep"
        ) as sleep:
            with patch(
                "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
                side_effect=(transient_failure, success),
            ) as run:
                result = runtime._run_manager_shell("docker stack deploy test")

        self.assertEqual(success, result)
        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_external_secret_exists_inspects_secret_with_option_boundary(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(
            runtime,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run_manager_shell:
            self.assertTrue(runtime.external_secret_exists("tsw_vaultwarden_admin_token"))

        run_manager_shell.assert_called_once_with(
            "docker secret inspect -- tsw_vaultwarden_admin_token >/dev/null 2>&1",
            check=False,
        )

    def test_ensure_external_secret_creates_missing_secret_without_leaking_value(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(
            runtime,
            "external_secret_exists",
            return_value=False,
        ) as external_secret_exists:
            with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
                runtime.ensure_external_secret(
                    "tsw_vaultwarden_admin_token",
                    operator_credential(),
                )

        external_secret_exists.assert_called_once_with("tsw_vaultwarden_admin_token")
        run_manager_shell.assert_called_once_with(
            "docker secret create -- tsw_vaultwarden_admin_token -",
            input_text=operator_credential(),
        )
        self.assertNotIn(operator_credential(), run_manager_shell.call_args.args[0])

    def test_ensure_external_secret_leaves_existing_secret_unchanged(self):
        runtime = LxcSwarmRuntime(backend=ManagedLxcBackend.LXD)

        with patch.object(runtime, "external_secret_exists", return_value=True):
            with patch.object(runtime, "_run_manager_shell") as run_manager_shell:
                runtime.ensure_external_secret(
                    "tsw_vaultwarden_admin_token",
                    operator_credential(),
                )

        run_manager_shell.assert_not_called()

    def test_container_runtime_runs_docker_inside_lxc_manager(self):
        runtime = LxcContainerRuntime(backend=ManagedLxcBackend.LXD)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, stdout="nexus.1.abc\n"),
        ) as run:
            self.assertEqual(runtime.find_container_names("nexus"), ["swarm-manager::nexus.1.abc"])

        run.assert_called_once()
        self.assertEqual(
            run.call_args.args[0][:5],
            ["lxc", "exec", "swarm-manager", "--", "docker"],
        )

    def test_container_runtime_finds_and_reads_containers_on_configured_lxc_nodes(self):
        runtime = LxcContainerRuntime(
            backend=ManagedLxcBackend.LXD,
            node_names=("swarm-manager", "swarm-worker-1"),
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0, stdout="nexus_nexus.1.abc\n"),
                subprocess.CompletedProcess([], 0, stdout=""),
                subprocess.CompletedProcess([], 0, stdout="initial-password\n"),
            ],
        ) as run:
            container_names = runtime.find_container_names("nexus")
            self.assertTrue(runtime.file_exists(container_names[0], "/nexus-data/admin.password"))
            self.assertEqual(
                runtime.read_file(container_names[0], "/nexus-data/admin.password"),
                "initial-password\n",
            )

        self.assertEqual(container_names, ["swarm-worker-1::nexus_nexus.1.abc"])
        self.assertEqual(
            run.call_args_list[-1].args[0][:7],
            ["lxc", "exec", "swarm-worker-1", "--", "docker", "exec", "nexus_nexus.1.abc"],
        )

    def test_manager_ip_reads_lxc_eth0_not_docker_bridge_address(self):
        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            return_value=subprocess.CompletedProcess(
                [],
                0,
                stdout=f"{ipv4_address(10, 156, 143, 201)}\n",
            ),
        ) as run:
            self.assertEqual(
                ipv4_address(10, 156, 143, 201),
                _lxc_manager_ip(ManagedLxcBackend.LXD, "swarm-manager", 30),
            )

        self.assertEqual(
            run.call_args.args[0],
            [
                "lxc",
                "exec",
                "swarm-manager",
                "--",
                "sh",
                "-lc",
                "ip -4 -o addr show dev eth0 | awk '{print $4}' | cut -d/ -f1",
            ],
        )

    def test_manager_ip_retries_transient_incus_child_pid_failure(self):
        transient = subprocess.CompletedProcess(
            [],
            255,
            stdout="",
            stderr="Error: Failed to retrieve PID of executing child process",
        )
        recovered = subprocess.CompletedProcess(
            [],
            0,
            stdout=f"{ipv4_address(10, 156, 143, 201)}\n",
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            side_effect=(transient, recovered),
        ) as run:
            with patch("tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.time.sleep"):
                self.assertEqual(
                    ipv4_address(10, 156, 143, 201),
                    _lxc_manager_ip(ManagedLxcBackend.LXD, "swarm-manager", 30),
                )

        self.assertEqual(run.call_count, 2)

    def test_image_publisher_pulls_public_image_without_local_registry_login(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "postgres",
            "14-alpine",
            "infisical-postgres",
            source="pull",
        )

        with patch.object(
            publisher,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess([], 1),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            with patch.object(publisher, "_docker_login") as docker_login:
                with patch.object(publisher, "_load_host_cached_image", return_value=False):
                    publisher.publish_image(contract)

        docker_login.assert_not_called()
        self.assertEqual(run_manager_shell.call_args_list[0].args[0], "docker image inspect postgres:14-alpine")
        run_manager_shell.assert_called_with(
            "docker pull postgres:14-alpine",
            check=False,
            operation="pull_public_image",
            timeout_seconds=1800,
        )

    def test_image_publisher_reuses_existing_manager_public_image(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "infisical/infisical",
            "v0.159.1",
            "infisical",
            source="pull",
        )

        with patch.object(
            publisher,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run_manager_shell:
            with patch.object(publisher, "_load_host_cached_image") as load_host_cache:
                publisher.publish_image(contract)

        load_host_cache.assert_not_called()
        run_manager_shell.assert_called_once_with(
            "docker image inspect infisical/infisical:v0.159.1",
            check=False,
            operation="inspect_cached_public_image",
            timeout_seconds=60,
        )

    def test_image_publisher_verifies_existing_manager_public_image_without_pull(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "infisical/infisical",
            "v0.159.1",
            "infisical",
            source="pull",
        )

        with patch.object(
            publisher,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run_manager_shell:
            with patch.object(publisher, "_docker_login") as docker_login:
                self.assertTrue(publisher.image_available(contract))

        docker_login.assert_not_called()
        run_manager_shell.assert_called_once_with(
            "docker image inspect infisical/infisical:v0.159.1",
            check=False,
            operation="inspect_cached_public_image",
            timeout_seconds=60,
        )

    def test_image_publisher_reuses_existing_manager_build_image(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "127.0.0.1:13500/jenkins",
            "0.2.0",
            "jenkins",
        )

        with patch.object(
            publisher,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run_manager_shell:
            with patch.object(publisher, "_transfer_context") as transfer_context:
                publisher.publish_image(contract)

        transfer_context.assert_not_called()
        run_manager_shell.assert_called_once_with(
            "docker image inspect 127.0.0.1:13500/jenkins:0.2.0",
            check=False,
            operation="inspect_cached_build_image",
            timeout_seconds=60,
        )

    def test_image_publisher_treats_missing_host_docker_cache_as_cache_miss(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "infisical/infisical",
            "v0.159.1",
            "infisical",
            source="pull",
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with patch.object(
                publisher,
                "_run_manager_shell",
                side_effect=(
                    subprocess.CompletedProcess([], 1),
                    subprocess.CompletedProcess([], 0),
                ),
            ) as run_manager_shell:
                publisher.publish_image(contract)

        self.assertEqual(
            run_manager_shell.call_args_list[0].args[0],
            "docker image inspect infisical/infisical:v0.159.1",
        )
        run_manager_shell.assert_called_with(
            "docker pull infisical/infisical:v0.159.1",
            check=False,
            operation="pull_public_image",
            timeout_seconds=1800,
        )

    def test_image_publisher_reports_public_image_rate_limit_without_payload(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "redis",
            "7-alpine",
            "infisical-redis",
            source="pull",
        )
        rejected = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr="toomanyrequests: You have reached your unauthenticated pull rate limit",
        )

        with patch.object(publisher, "_run_manager_shell", return_value=rejected):
            with patch.object(publisher, "_load_host_cached_image", return_value=False):
                with self.assertRaises(PublicImagePullRejected) as raised:
                    publisher.publish_image(contract)

        self.assertEqual(raised.exception.diagnostic, "registry_rate_limited")
        self.assertIn("registry mirror", raised.exception.operator_action)
        self.assertNotIn("toomanyrequests", str(raised.exception).lower())

    def test_image_publisher_reports_local_image_build_failure_without_raw_payload(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        result = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr=sensitive_assignment(),
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime.subprocess.run",
            return_value=result,
        ):
            with self.assertRaises(ImagePublisherOperationRejected) as raised:
                publisher._run_manager_shell(
                    "docker build -t 127.0.0.1:13500/service-access-dashboard:0.2.0 /tmp/context",
                    operation="build_image",
                    timeout_seconds=1800,
                )

        self.assertEqual(raised.exception.operation, "build_image")
        self.assertEqual(raised.exception.diagnostic, "image_build_failed")
        self.assertIn("image context", raised.exception.operator_action)
        self.assertNotIn(sensitive_assignment(), str(raised.exception))

    def test_image_publisher_uses_host_cached_image_when_public_pull_is_rate_limited(self):
        publisher = LxcContainerImagePublisher(
            backend=ManagedLxcBackend.LXD,
            registry_username="admin",
            registry_password=operator_credential(),
        )
        contract = ContainerImageContract(
            "infisical/infisical",
            "v0.159.1",
            "infisical",
            source="pull",
        )
        rejected = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr="toomanyrequests: You have reached your unauthenticated pull rate limit",
        )

        with patch.object(publisher, "_run_manager_shell", return_value=rejected):
            with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                publisher.publish_image(contract)

        self.assertEqual(
            run.call_args_list[0].args[0],
            ["docker", "image", "inspect", "infisical/infisical:v0.159.1"],
        )
        self.assertEqual(run.call_args_list[1].args[0][:2], ["bash", "-lc"])
        self.assertIn(
            "docker save infisical/infisical:v0.159.1",
            run.call_args_list[1].args[0][2],
        )
        self.assertIn("lxc exec swarm-manager -- docker load", run.call_args_list[1].args[0][2])

    def test_portainer_admin_client_raises_typed_rejection_for_failed_init(self):
        session = _FakeSession(
            [
                _FakeResponse(409, {"message": sensitive_assignment()}),
                _FakeResponse(200, ValueError(sensitive_assignment())),
            ]
        )
        client = LxcPortainerAdminClient(backend=ManagedLxcBackend.LXD, session=session)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            with self.assertRaises(PortainerAdminInitializationRejected) as raised:
                client.initialize_admin_user("admin", operator_credential())

        self.assertTrue(
            str(session.post_calls[0]["url"]).startswith(
                sample_http_url(ipv4_address(10, 156, 143, 201), 10001, "")
            )
        )
        self.assertIn("HTTP 409", str(raised.exception))
        self.assertEqual(raised.exception.status_code, 409)
        self.assertNotIn(sensitive_assignment(), str(raised.exception))

    def test_nexus_client_uses_direct_centralized_port_by_default(self):
        client = LxcNexusHttpClient(backend=ManagedLxcBackend.LXD, session=_FakeSession([]))

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            self.assertEqual(sample_http_url(ipv4_address(10, 156, 143, 201), 13081), client._base_url())

    def test_nexus_client_accepts_https_scheme_for_direct_access(self):
        client = LxcNexusHttpClient(
            backend=ManagedLxcBackend.LXD,
            scheme="https",
            session=_FakeSession([]),
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            self.assertEqual(client._base_url(), f"https://{ipv4_address(10, 156, 143, 201)}:13081")

    def test_nexus_client_rejects_invalid_direct_access_scheme(self):
        with self.assertRaises(ValueError):
            LxcNexusHttpClient(
                backend=ManagedLxcBackend.LXD,
                scheme="ftp",
                session=_FakeSession([]),
            )

    def test_portainer_admin_client_rejects_409_when_auth_probe_fails(self):
        session = _FakeSession(
            [
                _FakeResponse(409, {"message": "admin already initialized"}),
                requests.ConnectionError("Portainer auth endpoint unavailable."),
            ]
        )
        client = LxcPortainerAdminClient(backend=ManagedLxcBackend.LXD, session=session)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            with self.assertRaises(PortainerAdminInitializationRejected) as raised:
                client.initialize_admin_user("admin", operator_credential())

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(session.post_calls), 2)

    def test_portainer_admin_client_accepts_failed_init_when_authentication_works(self):
        password = operator_credential()
        session = _FakeSession(
            [
                _FakeResponse(409, {"message": "admin already initialized"}),
                _FakeResponse(200, {"jwt": "jwt-token"}),
            ]
        )
        client = LxcPortainerAdminClient(backend=ManagedLxcBackend.LXD, session=session)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            client.initialize_admin_user("admin", password)

        self.assertEqual(len(session.post_calls), 2)
        init_call, auth_call = session.post_calls
        self.assertTrue(str(init_call["url"]).endswith("/api/users/admin/init"))
        self.assertEqual(init_call["json"], {"username": "admin", "password": password})
        self.assertTrue(str(auth_call["url"]).endswith("/api/auth"))
        self.assertEqual(auth_call["json"], {"Username": "admin", "Password": password})

    def test_portainer_admin_client_clears_cookies_before_409_auth_probe(self):
        session = _FakeSession(
            [
                _FakeResponse(409, {"message": "admin already initialized"}),
                _FakeResponse(200, {"jwt": "jwt-token"}),
            ]
        )
        client = LxcPortainerAdminClient(backend=ManagedLxcBackend.LXD, session=session)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            client.initialize_admin_user("admin", operator_credential())

        self.assertEqual(session.cookies.clear_calls, 4)

    def test_portainer_admin_client_initializes_clean_state_without_followup_auth_probe(self):
        session = _FakeSession([_FakeResponse(200, {"message": "admin initialized"})])
        client = LxcPortainerAdminClient(backend=ManagedLxcBackend.LXD, session=session)

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value=ipv4_address(10, 156, 143, 201),
        ):
            client.initialize_admin_user("admin", operator_credential())

        self.assertEqual(len(session.post_calls), 1)
        self.assertTrue(str(session.post_calls[0]["url"]).endswith("/api/users/admin/init"))

    def test_lxc_portainer_client_creates_external_network_before_stack_create(self):
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
        )
        stack = StackDefinition(
            name="infisical",
            compose_content="""
services:
  infisical:
    image: infisical/infisical:v0.159.1
networks:
  service_access_link:
    name: service_access_link
    external: true
""",
        )
        delegate = _FakePortainerDelegate()

        with patch.object(
            client,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess([], 1),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            with patch.object(client, "_client", return_value=delegate):
                client.create_stack(stack, 1, {"TSW_EXAMPLE": "value"})

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertEqual(
            scripts,
            [
                "docker network inspect -- service_access_link >/dev/null 2>&1",
                "docker network create --driver overlay --attachable -- service_access_link >/dev/null",
            ],
        )
        self.assertEqual(delegate.created_stacks, [(stack, 1, {"TSW_EXAMPLE": "value"})])

    def test_lxc_portainer_client_reuses_existing_external_network(self):
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
        )
        stack = StackDefinition(
            name="service-access",
            compose_content="""
networks:
  service_access_link:
    name: service_access_link
    external: true
""",
        )

        with patch.object(
            client,
            "_run_manager_shell",
            return_value=subprocess.CompletedProcess([], 0),
        ) as run_manager_shell:
            with patch.object(client, "_client", return_value=_FakePortainerDelegate()):
                client.update_stack(7, stack, 1)

        run_manager_shell.assert_called_once_with(
            "docker network inspect -- service_access_link >/dev/null 2>&1",
            check=False,
        )

    def test_lxc_portainer_client_apply_stack_uses_gateway_and_overlay_preflight(self):
        from tiny_swarm_world.application.ports.clients.port_deployment_gateway import (
            DeploymentStackRequest,
        )
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
        )
        stack = StackDefinition(
            name="service-access",
            compose_content="""
networks:
  service_access_link:
    name: service_access_link
    external: true
""",
        )
        delegate = _FakePortainerDelegate(stack_id=None)

        with patch.object(
            client,
            "_run_manager_shell",
            side_effect=(
                subprocess.CompletedProcess([], 1),
                subprocess.CompletedProcess([], 0),
            ),
        ) as run_manager_shell:
            with patch.object(client, "_client", return_value=delegate):
                client.apply_stack(
                    DeploymentStackRequest(
                        target_stack="service-access",
                        stack_definition=stack,
                        stack_environment={"TSW_EXAMPLE": "value"},
                    )
                )

        scripts = [call.args[0] for call in run_manager_shell.call_args_list]
        self.assertEqual(
            scripts,
            [
                "docker network inspect -- service_access_link >/dev/null 2>&1",
                "docker network create --driver overlay --attachable -- service_access_link >/dev/null",
            ],
        )
        self.assertEqual(delegate.requested_endpoints, ["local"])
        self.assertEqual(delegate.requested_stacks, ["service-access"])
        self.assertEqual(delegate.created_stacks, [(stack, 1, {"TSW_EXAMPLE": "value"})])

    def test_lxc_portainer_client_reuses_delegate_for_workflow_lifetime(self):
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value="192.0.2.20",
        ):
            first = client._client()
            second = client._client()

        self.assertIs(first, second)
        self.assertEqual(sample_http_url("192.0.2.20", 10001), first.base_url)

    def test_lxc_portainer_client_accepts_https_scheme_for_delegate(self):
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
            scheme="https",
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value="192.0.2.20",
        ):
            self.assertEqual(client._client().base_url, "https://192.0.2.20:10001")

    def test_lxc_portainer_client_passes_stack_request_timeout_to_delegate(self):
        from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
            LxcPortainerHttpClient,
        )

        client = LxcPortainerHttpClient(
            backend=ManagedLxcBackend.LXD,
            username="admin",
            password=operator_credential(),
            timeout_seconds=17,
            stack_request_timeout_seconds=181,
        )

        with patch(
            "tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime._lxc_manager_ip",
            return_value="192.0.2.20",
        ):
            delegate = client._client()

        self.assertEqual(delegate.request_timeout_seconds, 17)
        self.assertEqual(delegate.stack_request_timeout_seconds, 181)


class _FakeResponse:
    def __init__(self, status_code: int, payload: object):
        self.status_code = status_code
        self.payload = payload

    def json(self) -> object:
        if isinstance(self.payload, ValueError):
            raise self.payload
        return self.payload


class _FakeSession:
    def __init__(self, post_responses: list[_FakeResponse | requests.RequestException]):
        self.post_responses = list(post_responses)
        self.post_calls: list[dict[str, object]] = []
        self.cookies = _FakeCookies()

    def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.post_calls.append({"url": url, **kwargs})
        response = self.post_responses.pop(0)
        if isinstance(response, requests.RequestException):
            raise response
        return response


class _FakePortainerDelegate:
    def __init__(self, stack_id: int | None = None) -> None:
        self.stack_id = stack_id
        self.requested_endpoints: list[str] = []
        self.requested_stacks: list[str] = []
        self.created_stacks: list[tuple[StackDefinition, int, dict[str, str]]] = []
        self.updated_stacks: list[tuple[int, StackDefinition, int, dict[str, str]]] = []

    def get_endpoint_id_by_name(self, endpoint_name: str) -> int:
        self.requested_endpoints.append(endpoint_name)
        return 1

    def find_stack_id_by_name(self, stack_name: str) -> int | None:
        self.requested_stacks.append(stack_name)
        return self.stack_id

    def create_stack(
        self,
        stack_definition: StackDefinition,
        endpoint_id: int,
        stack_environment: dict[str, str] | None = None,
    ) -> None:
        self.created_stacks.append(
            (stack_definition, endpoint_id, dict(stack_environment or {}))
        )

    def update_stack(
        self,
        stack_id: int,
        stack_definition: StackDefinition,
        endpoint_id: int,
        stack_environment: dict[str, str] | None = None,
    ) -> None:
        self.updated_stacks.append(
            (stack_id, stack_definition, endpoint_id, dict(stack_environment or {}))
        )


class _FakeCookies(dict[str, str]):
    def __init__(self):
        super().__init__()
        self.clear_calls = 0

    def clear(self) -> None:
        self.clear_calls += 1
        super().clear()
