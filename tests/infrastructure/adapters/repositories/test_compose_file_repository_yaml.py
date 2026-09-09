import tempfile
import tarfile
import unittest
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from urllib.parse import urlparse

from ruamel.yaml import YAML

from tiny_swarm_world.domain.artifacts import DEFAULT_CONTAINER_IMAGE_CONTRACTS
from tiny_swarm_world.domain.deployment import (
    DEFAULT_SERVICE_STACK_CONTRACTS,
    SERVICE_ACCESS_STACK_CONTRACT,
    ServiceStackProfile,
    service_stack_contracts_for_profile,
)
from tiny_swarm_world.domain.node_provider import ManagedLxcBackend
from tiny_swarm_world.domain.network import PortExposureClass, PortRegistry, ServicePortMapping
from tiny_swarm_world.domain.preflight import default_installation_plan
from tiny_swarm_world.infrastructure.adapters.clients.lxc_swarm_runtime import (
    LxcContainerImagePublisher,
)
from tiny_swarm_world.infrastructure.adapters.repositories.compose_file_repository_yaml import ComposeFileRepositoryYaml
from tiny_swarm_world.infrastructure.adapters.repositories.port_registry_yaml_repository import (
    PortRegistryYamlRepository,
)
from tests.support.effective_access_model_fixture import (
    CORE_ROUTE_EXPECTATIONS,
    OPTIONAL_ROUTE_EXPECTATIONS,
    effective_access_model_fixture,
)


class TestComposeFileRepositoryYaml(unittest.TestCase):
    def test_committed_installation_plan_matches_domain_plan(self):
        repository_root = Path(__file__).resolve().parents[4]
        yaml_plan = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "installation-plan.yaml").read_text(
                encoding="utf-8"
            )
        )
        domain_plan = default_installation_plan()

        self.assertEqual(
            set(domain_plan.required_phase_ids),
            set(yaml_plan["required_phase_ids"]),
        )
        self.assertEqual(
            set(domain_plan.required_services),
            set(yaml_plan["required_services"]),
        )
        yaml_phases = {phase["id"]: phase for phase in yaml_plan["phases"]}
        self.assertEqual(set(domain_plan.phase_ids), set(yaml_phases))

        for phase in domain_plan.phases:
            yaml_phase = yaml_phases[phase.phase_id]
            with self.subTest(phase=phase.phase_id):
                self.assertEqual(phase.order, yaml_phase["order"])
                self.assertEqual(phase.required, yaml_phase["required"])
                self.assertEqual(phase.depends_on, tuple(yaml_phase["depends_on"]))
                self.assertEqual(phase.services, tuple(yaml_phase["services"]))
                self.assertEqual(
                    phase.workflow_phase_names,
                    tuple(yaml_phase["workflow_phases"]),
                )

    def test_loads_compose_content_from_matching_stack_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            config_root = Path(temp_dir) / "config" / "compose"
            config_root.joinpath("nexus").mkdir(parents=True)
            compose_file = config_root / "nexus" / "docker-compose.yml"
            compose_file.write_text("services:\n  nexus:\n    image: nexus:latest\n    deploy: {}\n", encoding="utf-8")

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root, config_root])
            stack_definition = repository.get_compose_of("nexus")

            self.assertEqual(stack_definition.name, "nexus")
            self.assertIn("image: nexus:latest", stack_definition.compose_content)

    def test_direct_published_port_rewrite_updates_changed_registry_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            stack_root = compose_root / "jenkins"
            stack_root.mkdir(parents=True)
            stack_root.joinpath("docker-compose.yml").write_text(
                "\n".join(
                    (
                        "services:",
                        "  jenkins:",
                        "    image: jenkins/jenkins:lts",
                        "    deploy: {}",
                        "    ports:",
                        "      - target: 8080",
                        "        published: 8080",
                        "        protocol: tcp",
                        "        mode: host",
                    )
                ),
                encoding="utf-8",
            )
            registry = PortRegistry(
                ranges=(),
                mappings=(
                    ServicePortMapping(
                        service_id="jenkins",
                        port_id="jenkins-http",
                        internal_port=8080,
                        external_port=18080,
                        exposure=PortExposureClass.DIRECT,
                    ),
                ),
            )
            repository = ComposeFileRepositoryYaml(
                base_directories=[compose_root],
                port_registry=registry,
            )

            stack_definition = repository.get_compose_of("jenkins")
            compose_data = YAML(typ="safe").load(stack_definition.compose_content)

        self.assertEqual(compose_data["services"]["jenkins"]["ports"][0]["published"], 18080)
        self.assertEqual(compose_data["services"]["jenkins"]["ports"][0]["target"], 8080)

    def test_direct_published_port_rewrite_resolves_service_access_registry_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            stack_root = compose_root / "service-access"
            stack_root.mkdir(parents=True)
            stack_root.joinpath("docker-compose.yml").write_text(
                "\n".join(
                    (
                        "services:",
                        "  service-access-nginx:",
                        "    image: nginx:latest",
                        "    deploy: {}",
                        "    ports:",
                        "      - target: 80",
                        "        published: 10000",
                        "        protocol: tcp",
                        "        mode: host",
                    )
                ),
                encoding="utf-8",
            )
            registry = PortRegistry(
                ranges=(),
                mappings=(
                    ServicePortMapping(
                        service_id="service-access",
                        port_id="service-access-http",
                        internal_port=80,
                        external_port=10080,
                        exposure=PortExposureClass.DIRECT,
                    ),
                ),
            )
            repository = ComposeFileRepositoryYaml(
                base_directories=[compose_root],
                port_registry=registry,
            )

            with patch.object(repository, "render_service_access_dashboard", return_value=""):
                stack_definition = repository.get_compose_of("service-access")
            compose_data = YAML(typ="safe").load(stack_definition.compose_content)

        port = compose_data["services"]["service-access-nginx"]["ports"][0]
        self.assertEqual(port["published"], 10080)
        self.assertEqual(port["target"], 80)

    def test_direct_published_port_rewrite_rejects_missing_known_registry_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            stack_root = compose_root / "jenkins"
            stack_root.mkdir(parents=True)
            stack_root.joinpath("docker-compose.yml").write_text(
                "\n".join(
                    (
                        "services:",
                        "  jenkins:",
                        "    image: jenkins/jenkins:lts",
                        "    deploy: {}",
                        "    ports:",
                        "      - target: 8080",
                        "        published: 8080",
                        "        protocol: tcp",
                        "        mode: host",
                    )
                ),
                encoding="utf-8",
            )
            repository = ComposeFileRepositoryYaml(
                base_directories=[compose_root],
                port_registry=PortRegistry(ranges=(), mappings=()),
            )

            with self.assertRaisesRegex(ValueError, "jenkins-http.*missing"):
                repository.get_compose_of("jenkins")

    def test_direct_published_port_rewrite_preserves_optional_unpublished_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            stack_root = compose_root / "jenkins"
            stack_root.mkdir(parents=True)
            stack_root.joinpath("docker-compose.yml").write_text(
                "\n".join(
                    (
                        "services:",
                        "  jenkins:",
                        "    image: jenkins/jenkins:lts",
                        "    deploy: {}",
                        "    ports:",
                        "      - target: 8080",
                        "        published: 11080",
                        "        protocol: tcp",
                        "        mode: host",
                    )
                ),
                encoding="utf-8",
            )
            registry = PortRegistry(
                ranges=(),
                mappings=(
                    ServicePortMapping(
                        service_id="jenkins",
                        port_id="jenkins-http",
                        internal_port=8080,
                        external_port=None,
                        exposure=PortExposureClass.DIAGNOSTIC,
                    ),
                ),
            )
            repository = ComposeFileRepositoryYaml(
                base_directories=[compose_root],
                port_registry=registry,
            )

            stack_definition = repository.get_compose_of("jenkins")
            compose_data = YAML(typ="safe").load(stack_definition.compose_content)

        port = compose_data["services"]["jenkins"]["ports"][0]
        self.assertEqual(port["published"], 11080)
        self.assertEqual(port["target"], 8080)

    def test_extracts_service_names_and_published_ports_from_compose_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            compose_root.joinpath("mixed").mkdir(parents=True)
            compose_root.joinpath("mixed", "docker-compose.yml").write_text(
                """
services:
  web:
    image: nginx
    deploy: {}
    ports:
      - target: 80
        published: 8080
        protocol: tcp
        mode: host
      - "127.0.0.1:8443:443/tcp"
      - "9000"
  worker:
    image: busybox
    deploy: {}
  admin:
    image: nginx
    deploy: {}
    ports:
      - published: "9090"
        target: 90
""",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root])

            services = repository.get_services_of("mixed")

        self.assertEqual(
            [(service.name, service.published_ports) for service in services],
            [
                ("web", (8080, 8443)),
                ("worker", ()),
                ("admin", (9090,)),
            ],
        )
        self.assertEqual(
            [service.image_ref for service in services],
            ["nginx", "busybox", "nginx"],
        )

    def test_resolves_image_override_for_service_inventory_and_contracts(self):
        repository = ComposeFileRepositoryYaml(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
            environment={"TSW_NEXUS_IMAGE": "registry.local/nexus:3.76.0"},
        )

        services = repository.get_services_of("nexus")
        inventory = repository.get_image_inventory()
        nexus_requirement = next(
            requirement
            for requirement in inventory.requirements
            if requirement.service_name == "nexus:nexus"
        )

        self.assertEqual("registry.local/nexus:3.76.0", services[0].image_ref)
        self.assertEqual(nexus_requirement.image_ref, services[0].image_ref)
        self.assertEqual("nexus", nexus_requirement.build_context)
        self.assertTrue(inventory.valid)

    def test_profile_inventory_selects_only_the_profile_contracts(self):
        default_inventory = ComposeFileRepositoryYaml(
            service_profile=ServiceStackProfile.DEFAULT,
        ).get_image_inventory()
        service_access_inventory = ComposeFileRepositoryYaml(
            service_profile=ServiceStackProfile.SERVICE_ACCESS,
        ).get_image_inventory()

        self.assertTrue(default_inventory.valid)
        self.assertFalse(
            any(
                requirement.service_name.startswith(("infisical:", "service-access:"))
                for requirement in default_inventory.requirements
            )
        )
        self.assertTrue(service_access_inventory.valid)
        self.assertGreater(
            len(service_access_inventory.requirements),
            len(default_inventory.requirements),
        )

    def test_recursively_loads_compose_content_from_matching_stack_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            config_root = Path(temp_dir) / "config" / "compose"
            config_root.joinpath("platform", "services", "nexus").mkdir(parents=True)
            compose_file = config_root / "platform" / "services" / "nexus" / "docker-compose.yml"
            compose_file.write_text("services:\n  nexus:\n    image: nested\n    deploy: {}\n", encoding="utf-8")

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root, config_root])
            stack_definition = repository.get_compose_of("nexus")

            self.assertEqual(stack_definition.name, "nexus")
            self.assertIn("image: nested", stack_definition.compose_content)

    def test_prefers_first_matching_base_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            config_root = Path(temp_dir) / "config" / "compose"
            compose_root.joinpath("portainer").mkdir(parents=True)
            config_root.joinpath("portainer").mkdir(parents=True)
            compose_root.joinpath("portainer", "docker-compose.yml").write_text(
                "services:\n  portainer:\n    image: preferred\n    deploy: {}\n",
                encoding="utf-8",
            )
            config_root.joinpath("portainer", "docker-compose.yml").write_text(
                "services:\n  portainer:\n    image: fallback\n    deploy: {}\n",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root, config_root])
            stack_definition = repository.get_compose_of("portainer")

            self.assertIn("image: preferred", stack_definition.compose_content)
            self.assertNotIn("image: fallback", stack_definition.compose_content)

    def test_default_search_order_uses_config_compose(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath("config", "compose", "jenkins").mkdir(parents=True)
            root.joinpath("config", "compose", "jenkins", "docker-compose.yml").write_text(
                "services:\n  jenkins:\n    image: config-side\n    deploy: {}\n",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml()
            repository.base_directories = [root / "config" / "compose"]

            stack_definition = repository.get_compose_of("jenkins")

        self.assertIn("image: config-side", stack_definition.compose_content)

    def test_raises_when_stack_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            config_root = Path(temp_dir) / "config" / "compose"

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root, config_root])

            with self.assertRaises(FileNotFoundError):
                repository.get_compose_of("missing-stack")

    def test_rejects_stack_name_path_traversal(self):
        repository = ComposeFileRepositoryYaml(base_directories=[])

        with self.assertRaises(ValueError):
            repository.get_compose_of("../portainer")

    def test_rejects_invalid_stack_names(self):
        repository = ComposeFileRepositoryYaml(base_directories=[])

        for stack_name in ("", "../portainer", "/portainer", "Portainer", "portainer stack"):
            with self.subTest(stack_name=stack_name):
                with self.assertRaises(ValueError):
                    repository.get_compose_of(stack_name)

    def test_rejects_compose_file_without_services_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            compose_root.joinpath("broken").mkdir(parents=True)
            compose_root.joinpath("broken", "docker-compose.yml").write_text(
                "name: broken\n",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root])

            with self.assertRaisesRegex(ValueError, "non-empty services mapping"):
                repository.get_compose_of("broken")

    def test_rejects_compose_service_without_deploy_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            compose_root.joinpath("broken").mkdir(parents=True)
            compose_root.joinpath("broken", "docker-compose.yml").write_text(
                "services:\n  web:\n    image: nginx\n",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root])

            with self.assertRaisesRegex(ValueError, "web"):
                repository.get_compose_of("broken")

    def test_rejects_compose_service_with_non_mapping_deploy_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compose_root = Path(temp_dir) / "compose"
            compose_root.joinpath("broken").mkdir(parents=True)
            compose_root.joinpath("broken", "docker-compose.yml").write_text(
                "services:\n  web:\n    image: nginx\n    deploy: invalid\n",
                encoding="utf-8",
            )

            repository = ComposeFileRepositoryYaml(base_directories=[compose_root])

            with self.assertRaisesRegex(ValueError, "deploy mapping"):
                repository.get_compose_of("broken")

    def test_committed_portainer_compose_uses_docker_socket_mount(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "portainer" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")

        self.assertIn("/var/run/docker.sock:/var/run/docker.sock", compose_content)
        self.assertNotIn("/var/run/sock", compose_content)

    def test_committed_portainer_compose_provisions_admin_password_before_api_bootstrap(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "portainer" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")

        self.assertIn("--admin-password-file", compose_content)
        self.assertIn("/run/secrets/portainer_admin_password", compose_content)
        self.assertIn("name: tsw_portainer_admin_password", compose_content)
        self.assertIn("external: true", compose_content)

    def test_committed_default_service_stack_compose_files_are_loadable(self):
        repository = ComposeFileRepositoryYaml()

        loaded_stack_names = [
            repository.get_compose_of(contract.stack_name).name
            for contract in DEFAULT_SERVICE_STACK_CONTRACTS
        ]

        self.assertEqual(
            loaded_stack_names,
            ["portainer", "traefik", "nexus", "jenkins", "pulsar", "sonarqube", "swagger"],
        )

    def test_committed_default_service_stack_compose_files_declare_required_services(self):
        repository = ComposeFileRepositoryYaml()
        yaml = YAML(typ="safe")

        missing_services_by_stack: dict[str, list[str]] = {}
        for contract in DEFAULT_SERVICE_STACK_CONTRACTS:
            stack_definition = repository.get_compose_of(contract.stack_name)
            compose_data = yaml.load(stack_definition.compose_content)
            declared_services = set((compose_data.get("services") or {}).keys())
            missing_services = [
                service_name
                for service_name in contract.required_services
                if service_name not in declared_services
            ]
            if missing_services:
                missing_services_by_stack[contract.stack_name] = missing_services

        self.assertEqual({}, missing_services_by_stack)

    def test_committed_compose_metadata_exposes_service_names_and_published_ports(self):
        repository = ComposeFileRepositoryYaml()

        metadata = {
            stack: {
                service.name: service.published_ports
                for service in repository.get_services_of(stack)
            }
            for stack in (
                "jenkins",
                "infisical",
                "nexus",
                "portainer",
                "pulsar",
                "service-access",
                "sonarqube",
                "swagger",
                "traefik",
            )
        }

        self.assertEqual(metadata["jenkins"]["jenkins"], (11080, 11050))
        self.assertEqual(metadata["infisical"]["infisical"], (17080,))
        self.assertEqual(metadata["nexus"]["nexus"], (13081, 13500, 13501))
        self.assertEqual(metadata["service-access"]["service-access-nginx"], (10000, 8086))
        self.assertEqual(metadata["traefik"]["traefik"], (80, 443))

    def test_committed_service_registry_aligns_selected_stacks_with_phase_and_ports(self):
        repository_root = Path(__file__).resolve().parents[4]
        registry = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "services.yml").read_text(
                encoding="utf-8"
            )
        )
        service_entries = registry["services"]
        expected_stacks = YAML(typ="safe").load(
            (
                repository_root / "infra" / "config" / "inventory" / "desired_inventory.yaml"
            ).read_text(encoding="utf-8")
        )["expected_stacks"]
        plan_phase_ids = {phase.phase_id for phase in default_installation_plan().phases}
        registry_port_ids = {mapping.port_id for mapping in PortRegistryYamlRepository().load().mappings}
        contract_by_stack = {
            contract.stack_name: contract
            for contract in service_stack_contracts_for_profile(ServiceStackProfile.SERVICE_ACCESS)
        }

        self.assertLessEqual(set(expected_stacks), set(service_entries))
        selected_stacks = expected_stacks
        self.assertEqual(set(), set(service_entries) - set(expected_stacks))
        self.assertEqual(set(selected_stacks), set(contract_by_stack))
        self.assertEqual(
            set(service_entries),
            {
                "infisical",
                "jenkins",
                "nexus",
                "portainer",
                "pulsar",
                "service-access",
                "sonarqube",
                "swagger",
                "traefik",
            },
        )

        for stack_name in selected_stacks:
            entry = service_entries[stack_name]
            with self.subTest(stack_name=stack_name):
                contract = contract_by_stack[stack_name]
                self.assertTrue(entry["enabled"])
                self.assertEqual(stack_name, entry["stack"])
                self.assertEqual(contract.phase_id, entry["phase"])
                self.assertIn(entry["phase"], plan_phase_ids)
                self.assertEqual(list(contract.required_services), entry["required_services"])
                self.assertEqual(list(contract.port_ids), entry["port_ids"])
                self.assertEqual(contract.service_readiness_target_id, entry["readiness_target"])
                self.assertLessEqual(set(entry["port_ids"]), registry_port_ids)

        self.assertEqual(service_entries["traefik"]["phase"], "network-routing")
        self.assertEqual(service_entries["traefik"]["required_services"], ["traefik"])
        self.assertLessEqual(set(service_entries["traefik"]["port_ids"]), registry_port_ids)

    def test_committed_compose_published_ports_are_registry_ingress_or_compatibility(self):
        repository = ComposeFileRepositoryYaml()
        repository_root = Path(__file__).resolve().parents[4]
        service_entries = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "services.yml").read_text(
                encoding="utf-8"
            )
        )["services"]
        registry_ports_by_id = {
            mapping.port_id: mapping.external_port
            for mapping in PortRegistryYamlRepository().load().mappings
        }

        for stack_name, entry in service_entries.items():
            published_ports = {
                port
                for service in repository.get_services_of(stack_name)
                for port in service.published_ports
            }
            registry_published_ports = {
                registry_ports_by_id[port_id]
                for port_id in entry["port_ids"]
                if registry_ports_by_id[port_id] is not None
            }
            classified_ports = (
                set(entry.get("compatibility_published_ports", ()))
                | set(entry.get("deferred_published_ports", ()))
                | set(entry.get("ingress_published_ports", ()))
                | registry_published_ports
            )

            with self.subTest(stack_name=stack_name):
                self.assertLessEqual(published_ports, classified_ports)

    def test_service_access_legacy_port_is_explicit_compatibility_metadata(self):
        repository_root = Path(__file__).resolve().parents[4]
        repository = ComposeFileRepositoryYaml()
        registry = PortRegistryYamlRepository().load()
        legacy = next(
            mapping
            for mapping in registry.mappings
            if mapping.port_id == "service-access-legacy-http"
        )
        compose_data = YAML(typ="safe").load(
            repository.get_compose_of("service-access").compose_content
        )
        legacy_entry = compose_data["services"]["service-access-nginx"]["ports"][1]

        self.assertEqual(legacy.exposure, PortExposureClass.COMPATIBILITY)
        self.assertEqual(legacy.internal_port, 8086)
        self.assertEqual(legacy.external_port, 8086)
        self.assertEqual(legacy_entry["target"], legacy.internal_port)
        self.assertEqual(legacy_entry["published"], legacy.external_port)
        self.assertNotIn(
            "rabbitmq",
            "\n".join(
                path.read_text(encoding="utf-8").lower()
                for path in (repository_root / "infra" / "config").rglob("*")
                if path.is_file()
            ),
        )

    def test_all_active_compose_ports_match_registry_contract(self):
        repository_root = Path(__file__).resolve().parents[4]
        repository = ComposeFileRepositoryYaml()
        expected = {
            ("portainer", "portainer", 9000): ("portainer-http", 10001),
            ("jenkins", "jenkins", 8080): ("jenkins-http", 11080),
            ("jenkins", "jenkins", 50000): ("jenkins-agent", 11050),
            ("nexus", "nexus", 8081): ("nexus-http", 13081),
            ("nexus", "nexus", 5000): ("nexus-docker-http", 13500),
            ("nexus", "nexus", 5001): ("nexus-docker-https", 13501),
            ("infisical", "infisical", 8080): ("infisical-http", 17080),
            ("pulsar", "pulsar", 6650): ("pulsar-broker", 14001),
            ("pulsar", "pulsar", 8080): ("pulsar-admin-api", 14080),
            ("pulsar", "pulsar-manager", 9527): ("pulsar-manager-gui", 14081),
            ("sonarqube", "sonarqube", 9000): ("sonarqube-http", 12000),
            ("swagger", "swagger-ui", 8080): ("swagger-ui", 16080),
            ("swagger", "swagger-nginx", 8084): ("openapi-aggregator", 16081),
            ("traefik", "traefik", 80): ("traefik-http", 80),
            ("traefik", "traefik", 443): ("traefik-https", 443),
            ("service-access", "service-access-nginx", 80): (
                "service-access-http",
                10000,
            ),
            ("service-access", "service-access-nginx", 8086): (
                "service-access-legacy-http",
                8086,
            ),
        }
        registry_by_id = {
            mapping.port_id: mapping
            for mapping in PortRegistryYamlRepository().load().mappings
        }
        actual = set()
        for stack_name in sorted({key[0] for key in expected}):
            compose_data = YAML(typ="safe").load(
                repository.get_compose_of(stack_name).compose_content
            )
            for service_name, service_payload in compose_data["services"].items():
                for entry in service_payload.get("ports", ()):
                    if isinstance(entry, dict) and isinstance(entry.get("target"), int):
                        actual.add((stack_name, service_name, entry["target"]))

        self.assertEqual(actual, set(expected))
        for key, (port_id, published) in expected.items():
            with self.subTest(port_id=port_id):
                mapping = registry_by_id[port_id]
                self.assertEqual(mapping.internal_port, key[2])
                self.assertEqual(mapping.external_port, published)

        compose_root = repository_root / "infra" / "config" / "compose"
        for absent_stack in ("prometheus", "grafana"):
            with self.subTest(absent_stack=absent_stack):
                self.assertFalse((compose_root / absent_stack / "docker-compose.yml").exists())
                self.assertNotIn(
                    f"{absent_stack}-http",
                    {port_id for port_id, _ in expected.values()},
                )

    def test_committed_health_checks_align_with_services_and_contracts(self):
        repository_root = Path(__file__).resolve().parents[4]
        health_checks = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "health-checks.yaml").read_text(
                encoding="utf-8"
            )
        )["checks"]
        service_entries = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "services.yml").read_text(
                encoding="utf-8"
            )
        )["services"]
        contract_by_stack = {
            contract.stack_name: contract
            for contract in service_stack_contracts_for_profile(ServiceStackProfile.SERVICE_ACCESS)
        }
        plan_phase_ids = {phase.phase_id for phase in default_installation_plan().phases}

        ids = [check["id"] for check in health_checks]
        target_ids = [check["target_id"] for check in health_checks]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(target_ids), len(set(target_ids)))

        checks_by_stack = {check["stack"]: check for check in health_checks}
        self.assertEqual(set(service_entries), set(checks_by_stack))
        for stack_name, entry in service_entries.items():
            check = checks_by_stack[stack_name]
            with self.subTest(stack_name=stack_name):
                self.assertFalse(check["live_default"])
                self.assertEqual(check["evidence_kind"], "swarm_service_replicas")
                self.assertEqual(entry["readiness_target"], check["target_id"])
                self.assertEqual(entry["phase"], check["phase"])
                self.assertIn(check["phase"], plan_phase_ids)
                self.assertEqual(entry["required_services"], check["required_services"])
                if stack_name in contract_by_stack:
                    contract = contract_by_stack[stack_name]
                    self.assertEqual(contract.service_readiness_target_id, check["target_id"])
                    self.assertEqual(list(contract.required_services), check["required_services"])

    def test_committed_validation_plan_covers_required_health_check_targets(self):
        repository_root = Path(__file__).resolve().parents[4]
        health_checks = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "health-checks.yaml").read_text(
                encoding="utf-8"
            )
        )["checks"]
        validation_plan = YAML(typ="safe").load(
            (repository_root / "infra" / "config" / "validation-plan.yaml").read_text(
                encoding="utf-8"
            )
        )["plans"]["greenpath"]
        health_targets = {check["target_id"] for check in health_checks}
        required_targets = validation_plan["required_targets"]

        self.assertFalse(validation_plan["live_default"])
        self.assertEqual(len(required_targets), len(set(required_targets)))
        self.assertEqual(health_targets, set(required_targets))
        self.assertEqual(validation_plan["optional_targets"], [])

    def test_committed_jenkins_compose_uses_overridable_registry_image(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = (
            repository_root / "infra" / "config" / "compose" / "jenkins" / "docker-compose.yml"
        )
        compose_data = YAML(typ="safe").load(compose_path.read_text(encoding="utf-8"))

        self.assertEqual(
            compose_data["services"]["jenkins"]["image"],
            "${TSW_JENKINS_IMAGE:-127.0.0.1:13500/jenkins:0.2.0}",
        )
        self.assertEqual(
            compose_data["services"]["jenkins"]["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )
        self.assertEqual(
            compose_data["services"]["jenkins"]["ports"],
            [
                {"target": 8080, "published": 11080, "protocol": "tcp", "mode": "host"},
                {"target": 50000, "published": 11050, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertEqual(
            compose_data["services"]["jenkins"]["volumes"],
            ["jenkins_home:/var/lib/jenkins"],
        )
        self.assertEqual(
            compose_data["services"]["jenkins"]["environment"],
            {"TSW_JENKINS_ADMIN_PASSWORD": "${TSW_JENKINS_ADMIN_PASSWORD}"},
        )
        self.assertNotIn("secrets", compose_data)
        self.assertNotEqual(compose_data["services"]["jenkins"].get("user"), "root")

    def test_committed_nexus_compose_publishes_registry_ports_on_manager_host(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = (
            repository_root / "infra" / "config" / "compose" / "nexus" / "docker-compose.yml"
        )
        compose_data = YAML(typ="safe").load(compose_path.read_text(encoding="utf-8"))
        nexus = compose_data["services"]["nexus"]

        self.assertEqual(
            nexus["ports"],
            [
                {"target": 8081, "published": 13081, "protocol": "tcp", "mode": "host"},
                {"target": 5000, "published": 13500, "protocol": "tcp", "mode": "host"},
                {"target": 5001, "published": 13501, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertEqual(
            nexus["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )

    def test_core_compose_stacks_render_registry_ports_without_changing_targets(self):
        registry = PortRegistry(
            ranges=(),
            mappings=(
                ServicePortMapping(
                    service_id="portainer",
                    port_id="portainer-http",
                    internal_port=9000,
                    external_port=20001,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="jenkins",
                    port_id="jenkins-http",
                    internal_port=8080,
                    external_port=20002,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="jenkins",
                    port_id="jenkins-agent",
                    internal_port=50000,
                    external_port=20003,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="sonarqube",
                    port_id="sonarqube-http",
                    internal_port=9000,
                    external_port=20004,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="nexus",
                    port_id="nexus-http",
                    internal_port=8081,
                    external_port=20005,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="nexus",
                    port_id="nexus-docker-http",
                    internal_port=5000,
                    external_port=None,
                    exposure=PortExposureClass.DIAGNOSTIC,
                ),
                ServicePortMapping(
                    service_id="nexus",
                    port_id="nexus-docker-https",
                    internal_port=5001,
                    external_port=None,
                    exposure=PortExposureClass.DIAGNOSTIC,
                ),
            ),
        )
        repository = ComposeFileRepositoryYaml(port_registry=registry)

        expected_ports = {
            "portainer": [(9000, 20001)],
            "jenkins": [(8080, 20002), (50000, 20003)],
            "sonarqube": [(9000, 20004)],
            "nexus": [(8081, 20005), (5000, 13500), (5001, 13501)],
        }
        for stack_name, expected in expected_ports.items():
            with self.subTest(stack_name=stack_name):
                stack_definition = repository.get_compose_of(stack_name)
                compose_data = YAML(typ="safe").load(stack_definition.compose_content)
                service_name = next(iter(compose_data["services"]))
                actual = [
                    (port["target"], port["published"])
                    for port in compose_data["services"][service_name]["ports"]
                ]
                self.assertEqual(actual, expected)

    def test_messaging_gateway_swagger_and_access_stacks_render_registry_ports(self):
        registry = PortRegistry(
            ranges=(),
            mappings=(
                ServicePortMapping(
                    service_id="pulsar",
                    port_id="pulsar-broker",
                    internal_port=6650,
                    external_port=24001,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="pulsar",
                    port_id="pulsar-admin-api",
                    internal_port=8080,
                    external_port=24080,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="pulsar-manager",
                    port_id="pulsar-manager-gui",
                    internal_port=9527,
                    external_port=24081,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="traefik",
                    port_id="traefik-http",
                    internal_port=80,
                    external_port=80,
                    exposure=PortExposureClass.PUBLIC_INGRESS,
                ),
                ServicePortMapping(
                    service_id="traefik",
                    port_id="traefik-https",
                    internal_port=443,
                    external_port=443,
                    exposure=PortExposureClass.PUBLIC_INGRESS,
                ),
                ServicePortMapping(
                    service_id="swagger",
                    port_id="swagger-ui",
                    internal_port=8080,
                    external_port=26080,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="swagger",
                    port_id="openapi-aggregator",
                    internal_port=8084,
                    external_port=26081,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="service-access",
                    port_id="service-access-http",
                    internal_port=80,
                    external_port=21080,
                    exposure=PortExposureClass.DIRECT,
                ),
                ServicePortMapping(
                    service_id="infisical",
                    port_id="infisical-http",
                    internal_port=8080,
                    external_port=27080,
                    exposure=PortExposureClass.DIRECT,
                ),
            ),
        )
        repository = ComposeFileRepositoryYaml(port_registry=registry)
        expected_ports = {
            "pulsar": {
                "pulsar": [(6650, 24001), (8080, 24080)],
                "pulsar-manager": [(9527, 24081)],
            },
            "traefik": {"traefik": [(80, 80), (443, 443)]},
            "swagger": {
                "swagger-ui": [(8080, 26080)],
                "swagger-nginx": [(8084, 26081)],
            },
            "service-access": {
                "service-access-nginx": [(80, 21080), (8086, 8086)],
            },
            "infisical": {"infisical": [(8080, 27080)]},
        }

        for stack_name, expected_services in expected_ports.items():
            with self.subTest(stack_name=stack_name):
                if stack_name == "service-access":
                    with patch.object(repository, "render_service_access_dashboard", return_value=""):
                        stack_definition = repository.get_compose_of(stack_name)
                else:
                    stack_definition = repository.get_compose_of(stack_name)
                compose_data = YAML(typ="safe").load(stack_definition.compose_content)
                for service_name, expected in expected_services.items():
                    actual = [
                        (port["target"], port["published"])
                        for port in compose_data["services"][service_name]["ports"]
                    ]
                    self.assertEqual(actual, expected)

    def test_active_config_does_not_reintroduce_rabbitmq(self):
        repository_root = Path(__file__).resolve().parents[4]
        config_root = repository_root / "infra" / "config"
        for config_path in config_root.rglob("*"):
            if config_path.is_file():
                with self.subTest(config_path=config_path):
                    self.assertNotIn("rabbitmq", config_path.read_text(encoding="utf-8").lower())

    def test_committed_pulsar_compose_uses_standalone_with_non_conflicting_admin_port(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = (
            repository_root / "infra" / "config" / "compose" / "pulsar" / "docker-compose.yml"
        )
        compose_data = YAML(typ="safe").load(compose_path.read_text(encoding="utf-8"))
        pulsar = compose_data["services"]["pulsar"]

        self.assertEqual(
            pulsar["image"],
            "${TSW_PULSAR_IMAGE:-apachepulsar/pulsar:3.0.17}",
        )
        self.assertEqual(pulsar["command"][:2], ["sh", "-lc"])
        self.assertIn("bin/apply-config-from-env.py conf/standalone.conf", pulsar["command"][-1])
        self.assertNotIn("bin/apply-config-from-env.py conf/bookkeeper.conf", pulsar["command"][-1])
        self.assertIn("exec bin/pulsar standalone", pulsar["command"][-1])
        self.assertIn("--advertised-address 127.0.0.1", pulsar["command"][-1])
        self.assertIn("--bookkeeper-port 3181", pulsar["command"][-1])
        self.assertIn("--no-functions-worker", pulsar["command"][-1])
        self.assertIn("--no-stream-storage", pulsar["command"][-1])
        self.assertEqual(pulsar["environment"]["PULSAR_PREFIX_authenticationEnabled"], "true")
        self.assertEqual(pulsar["environment"]["PULSAR_PREFIX_advertisedAddress"], "127.0.0.1")
        self.assertEqual(
            pulsar["environment"]["PULSAR_PREFIX_ledgerStorageClass"],
            "org.apache.bookkeeper.bookie.InterleavedLedgerStorage",
        )
        self.assertNotIn("PULSAR_PREFIX_zookeeperServers", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_zkServers", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_configurationStoreServers", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_metadataStoreUrl", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_configurationMetadataStoreUrl", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_metadataServiceUri", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_zooKeeperOperationTimeoutSeconds", pulsar["environment"])
        self.assertNotIn("PULSAR_PREFIX_zooKeeperSessionTimeoutMillis", pulsar["environment"])
        self.assertIn(
            "AuthenticationProviderToken",
            pulsar["environment"]["PULSAR_PREFIX_authenticationProviders"],
        )
        self.assertEqual(
            pulsar["environment"]["PULSAR_PREFIX_tokenSecretKey"],
            "data:;base64,${TSW_PULSAR_TOKEN_SECRET_KEY}",
        )
        self.assertNotIn("PULSAR_PREFIX_bookieId", pulsar["environment"])
        self.assertEqual(
            pulsar["environment"]["PULSAR_MEM"],
            "-Xms512m -Xmx512m -XX:MaxDirectMemorySize=256m",
        )
        self.assertEqual(
            pulsar["environment"]["PULSAR_GC"],
            "-XX:+UseG1GC -XX:+PerfDisableSharedMem",
        )
        self.assertEqual(pulsar["environment"]["PULSAR_GC_LOG"], "")
        self.assertEqual(
            pulsar["environment"]["PULSAR_EXTRA_OPTS"],
            "-Djava.security.egd=file:/dev/./urandom -XX:TieredStopAtLevel=1 -XX:CICompilerCount=2",
        )
        self.assertEqual(pulsar["environment"]["TSW_PULSAR_ADMIN_TOKEN"], "${TSW_PULSAR_ADMIN_TOKEN}")
        self.assertEqual(
            pulsar["ports"],
            [
                {"target": 6650, "published": 14001, "protocol": "tcp", "mode": "host"},
                {"target": 8080, "published": 14080, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertNotIn(
            {"target": 8080, "published": 8080, "protocol": "tcp"},
            pulsar["ports"],
        )
        self.assertEqual(pulsar["volumes"], ["pulsar-data:/pulsar/data"])
        self.assertIn("healthcheck", pulsar)
        self.assertIn("http://localhost:8080/admin/v2/clusters", pulsar["healthcheck"]["test"][-1])
        self.assertIn("TSW_PULSAR_ADMIN_TOKEN", pulsar["healthcheck"]["test"][-1])
        self.assertEqual(pulsar["networks"], ["service_access_link"])
        self.assertEqual(
            compose_data["networks"]["service_access_link"],
            {"name": "service_access_link", "external": True},
        )
        self.assertEqual(
            pulsar["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )

        pulsar_manager = compose_data["services"]["pulsar-manager"]
        self.assertEqual(
            pulsar_manager["image"],
            "${TSW_PULSAR_MANAGER_IMAGE:-apachepulsar/pulsar-manager:v0.4.0}",
        )
        self.assertEqual(
            pulsar_manager["environment"]["SPRING_CONFIGURATION_FILE"],
            "/pulsar-manager/pulsar-manager/application.properties",
        )
        self.assertEqual(
            pulsar_manager["ports"],
            [
                {"target": 9527, "published": 14081, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertEqual(pulsar_manager["expose"], ["7750"])
        self.assertEqual(pulsar_manager["networks"], ["service_access_link"])
        self.assertEqual(
            pulsar_manager["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )

        bootstrap = compose_data["services"]["pulsar-manager-bootstrap"]
        self.assertEqual(
            bootstrap["image"],
            "${TSW_PULSAR_MANAGER_BOOTSTRAP_IMAGE:-python:3.12.13-alpine3.23}",
        )
        self.assertEqual(
            bootstrap["environment"]["TSW_PULSAR_MANAGER_ADMIN_PASSWORD"],
            "${TSW_PULSAR_MANAGER_ADMIN_PASSWORD}",
        )
        self.assertIn("users/superuser", bootstrap["command"][-1])
        self.assertIn("admin@example.org", bootstrap["command"][-1])
        self.assertIn("pulsar-manager/login", bootstrap["command"][-1])
        self.assertIn('"username": "admin"', bootstrap["command"][-1])
        self.assertIn('"Host": backend_host_header', bootstrap["command"][-1])
        self.assertEqual(
            bootstrap["environment"]["TSW_PULSAR_MANAGER_BACKEND_URL"],
            "http://tasks.pulsar-manager:7750",
        )
        self.assertIn("backend_host_header = \"localhost:7750\"", bootstrap["command"][-1])
        self.assertIn("api_rejected_superuser", bootstrap["command"][-1])
        self.assertIn("exc.code != 400", bootstrap["command"][-1])
        self.assertIn('response.get("login") == "success"', bootstrap["command"][-1])
        self.assertIn("json.dumps", bootstrap["command"][-1])
        self.assertEqual(bootstrap["deploy"]["update_config"]["failure_action"], "continue")
        self.assertEqual(bootstrap["deploy"]["restart_policy"]["condition"], "on-failure")
        self.assertEqual(bootstrap["deploy"]["restart_policy"]["delay"], "5s")
        self.assertEqual(bootstrap["deploy"]["restart_policy"]["max_attempts"], 3)

    def test_committed_swagger_compose_uses_official_images_and_remote_openapi_bind(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "swagger" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")
        yaml = YAML(typ="safe")
        compose_data = yaml.load(compose_content)

        self.assertIn("image: swaggerapi/swagger-editor:v5.6.2-unprivileged", compose_content)
        self.assertIn("image: swaggerapi/swagger-ui:v5.32.6", compose_content)
        self.assertIn("image: nginx:1.29.8-alpine", compose_content)
        self.assertNotIn("ports", compose_data["services"]["swagger-editor"])
        self.assertNotIn("ports", compose_data["services"]["swagger-api"])
        self.assertEqual(
            compose_data["services"]["swagger-nginx"]["ports"],
            [{"target": 8084, "published": 16081, "protocol": "tcp", "mode": "host"}],
        )
        self.assertIn("SWAGGER_JSON: /openapi.json", compose_content)
        self.assertIn(
            "${TSW_REMOTE_STACK_ROOT:-/var/lib/tiny-swarm-world/stacks}/swagger/swagger/openapi.json:/openapi.json:ro",
            compose_content,
        )
        self.assertIn(
            "${TSW_REMOTE_STACK_ROOT:-/var/lib/tiny-swarm-world/stacks}/swagger/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro",
            compose_content,
        )
        self.assertNotIn("127.0.0.1:5000/swagger-nginx", compose_content)
        self.assertNotIn("depends_on", compose_content)
        self.assertNotIn("./swagger/openapi.json:/openapi.json", compose_content)

    def test_committed_sonarqube_compose_waits_for_database_tcp_readiness(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = (
            repository_root / "infra" / "config" / "compose" / "sonarqube" / "docker-compose.yml"
        )
        compose_data = YAML(typ="safe").load(compose_path.read_text(encoding="utf-8"))
        entrypoint = compose_data["services"]["sonarqube"]["entrypoint"]
        command = compose_data["services"]["sonarqube"]["command"]

        self.assertEqual(tuple(entrypoint), ("bash", "-lc"))
        self.assertEqual(
            compose_data["services"]["sonarqube"]["environment"]["SONAR_JDBC_URL"],
            "jdbc:postgresql://tasks.sonar_db:5432/sonar",
        )
        self.assertIn("/dev/tcp/tasks.sonar_db/5432", command[0])
        self.assertIn("/opt/sonarqube/docker/entrypoint.sh", command[0])
        self.assertIn("service_access_link", compose_data["services"]["sonarqube"]["networks"])
        self.assertIn("service_access_link", compose_data["services"]["sonar_db"]["networks"])
        self.assertEqual(
            compose_data["services"]["sonarqube"]["ports"],
            [{"target": 9000, "published": 12000, "protocol": "tcp", "mode": "host"}],
        )
        self.assertEqual(
            compose_data["services"]["sonarqube"]["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )
        self.assertEqual(
            compose_data["networks"]["service_access_link"],
            {"name": "service_access_link", "external": True},
        )

    def test_committed_sonarqube_compose_uses_available_community_image(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = (
            repository_root / "infra" / "config" / "compose" / "sonarqube" / "docker-compose.yml"
        )
        compose_data = YAML(typ="safe").load(compose_path.read_text(encoding="utf-8"))

        self.assertEqual(
            compose_data["services"]["sonarqube"]["image"],
            "sonarqube:26.6.0.123539-community",
        )
        self.assertNotEqual(
            compose_data["services"]["sonarqube"]["image"],
            "sonarqube:lts-community",
        )

    def test_committed_service_access_compose_declares_required_services(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "service-access" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")
        compose_data = YAML(typ="safe").load(compose_content)
        services = compose_data["services"]

        self.assertEqual(ComposeFileRepositoryYaml().get_compose_of("service-access").name, "service-access")
        self.assertEqual(set(SERVICE_ACCESS_STACK_CONTRACT.required_services), set(services))
        self.assertEqual(
            services["service-access-dashboard"]["image"],
            "${TSW_SERVICE_ACCESS_DASHBOARD_IMAGE:-127.0.0.1:13500/service-access-dashboard:0.2.0}",
        )
        self.assertEqual(
            services["service-access-nginx"]["image"],
            "${TSW_SERVICE_ACCESS_NGINX_IMAGE:-127.0.0.1:13500/service-access-nginx:0.2.0}",
        )
        self.assertEqual(
            services["service-access-nginx"]["ports"],
            [
                {"target": 80, "published": 10000, "protocol": "tcp", "mode": "host"},
                {"target": 8086, "published": 8086, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertNotIn("secrets", compose_data)
        self.assertNotIn("volumes", compose_data)
        self.assertEqual(
            services["service-access-dashboard"]["configs"],
            [
                {
                    "source": "service_access_dashboard_index",
                    "target": "/usr/share/nginx/html/index.html",
                }
            ],
        )
        self.assertEqual(
            (
                compose_data["configs"]["service_access_dashboard_index"]["file"]
            ),
            "${TSW_REMOTE_STACK_ROOT:-/var/lib/tiny-swarm-world/stacks}"
                "/service-access/dashboard/index.html",
        )
        self.assertEqual(
            compose_data["networks"]["service_access_link"],
            {"name": "service_access_link", "external": True},
        )

    def test_committed_infisical_compose_declares_required_services_and_secret_boundary(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "infisical" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")
        compose_data = YAML(typ="safe").load(compose_content)
        services = compose_data["services"]

        self.assertEqual(ComposeFileRepositoryYaml().get_compose_of("infisical").name, "infisical")
        self.assertEqual(set(services), {"infisical", "infisical-db", "infisical-redis"})
        self.assertEqual(
            services["infisical"]["image"],
            "${TSW_INFISICAL_IMAGE:-infisical/infisical:v0.159.1}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["SITE_URL"],
            "${TSW_INFISICAL_SITE_URL:-http://localhost:17080}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["ENCRYPTION_KEY"],
            "${TSW_INFISICAL_ENCRYPTION_KEY}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["AUTH_SECRET"],
            "${TSW_INFISICAL_AUTH_SECRET}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["INITIAL_BOOTSTRAP_ADMIN_EMAIL"],
            "${TSW_INFISICAL_LOGIN_EMAIL}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["INITIAL_BOOTSTRAP_ADMIN_PASSWORD"],
            "${TSW_INFISICAL_BOOTSTRAP_ADMIN_PASSWORD}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["INITIAL_BOOTSTRAP_ADMIN_FIRST_NAME"],
            "${TSW_INFISICAL_ADMIN_FIRST_NAME:-Tiny}",
        )
        self.assertEqual(
            services["infisical"]["environment"]["INITIAL_BOOTSTRAP_ADMIN_LAST_NAME"],
            "${TSW_INFISICAL_ADMIN_LAST_NAME:-Admin}",
        )
        self.assertEqual(
            services["infisical"]["ports"],
            [{"target": 8080, "published": 17080, "protocol": "tcp", "mode": "host"}],
        )
        self.assertEqual(
            services["infisical"]["deploy"]["placement"]["constraints"],
            ["node.role == manager"],
        )
        self.assertNotIn("secrets", compose_data)
        self.assertEqual(services["infisical-db"]["volumes"], ["infisical_pg_data:/var/lib/postgresql/data"])
        self.assertEqual(services["infisical-redis"]["volumes"], ["infisical_redis_data:/data"])
        self.assertEqual(
            compose_data["networks"]["service_access_link"],
            {"name": "service_access_link", "external": True},
        )

    def test_committed_traefik_compose_defines_secure_swarm_ingress(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_path = repository_root / "infra" / "config" / "compose" / "traefik" / "docker-compose.yml"
        compose_content = compose_path.read_text(encoding="utf-8")
        compose_data = YAML(typ="safe").load(compose_content)
        traefik = compose_data["services"]["traefik"]
        command = traefik["command"]

        self.assertEqual(ComposeFileRepositoryYaml().get_compose_of("traefik").name, "traefik")
        self.assertEqual(traefik["image"], "${TSW_TRAEFIK_IMAGE:-traefik:v3.7.4}")
        self.assertIn("--entrypoints.web.address=:80", command)
        self.assertIn("--entrypoints.websecure.address=:443", command)
        self.assertIn("--entrypoints.web.http.redirections.entrypoint.to=websecure", command)
        self.assertIn("--providers.swarm=true", command)
        self.assertIn("--providers.swarm.exposedByDefault=false", command)
        self.assertIn("--providers.swarm.network=service_access_link", command)
        self.assertIn("--providers.file.filename=/etc/traefik/dynamic/tls.yml", command)
        self.assertNotIn("--api.insecure=true", compose_content)
        self.assertEqual(
            traefik["ports"],
            [
                {"target": 80, "published": 80, "protocol": "tcp", "mode": "host"},
                {"target": 443, "published": 443, "protocol": "tcp", "mode": "host"},
            ],
        )
        self.assertEqual(
            compose_data["networks"]["service_access_link"],
            {"name": "service_access_link", "external": True},
        )
        self.assertEqual(
            compose_data["configs"]["traefik_tls_dynamic_config"]["file"],
            "${TSW_REMOTE_STACK_ROOT:-/var/lib/tiny-swarm-world/stacks}/traefik/dynamic/tls.yml",
        )
        self.assertEqual(
            compose_data["secrets"]["traefik_tls_cert"],
            {
                "name": "${TSW_TRAEFIK_TLS_CERT_SECRET_NAME:-tsw_traefik_tls_cert}",
                "external": True,
            },
        )
        self.assertEqual(
            compose_data["secrets"]["traefik_tls_key"],
            {
                "name": "${TSW_TRAEFIK_TLS_KEY_SECRET_NAME:-tsw_traefik_tls_key}",
                "external": True,
            },
        )
        self.assertEqual(
            compose_data["secrets"]["traefik_gui_users"],
            {
                "name": "${TSW_TRAEFIK_GUI_USERS_SECRET_NAME:-tsw_traefik_gui_users}",
                "external": True,
            },
        )
        self.assertEqual(
            traefik["secrets"][0]["source"],
            "traefik_tls_cert",
        )
        self.assertEqual(traefik["secrets"][0]["target"], "tsw_traefik_tls_cert")
        self.assertEqual(
            traefik["secrets"][1]["source"],
            "traefik_tls_key",
        )
        self.assertEqual(traefik["secrets"][1]["target"], "tsw_traefik_tls_key")
        self.assertEqual(traefik["secrets"][2]["source"], "traefik_gui_users")
        self.assertEqual(traefik["secrets"][2]["target"], "tsw_traefik_gui_users")

    def test_committed_traefik_dynamic_tls_config_references_secret_mounts_only(self):
        repository_root = Path(__file__).resolve().parents[4]
        tls_path = repository_root / "infra" / "config" / "compose" / "traefik" / "dynamic" / "tls.yml"
        tls_content = tls_path.read_text(encoding="utf-8")
        tls_data = YAML(typ="safe").load(tls_content)

        certificate = tls_data["tls"]["certificates"][0]
        self.assertEqual(certificate["certFile"], "/run/secrets/tsw_traefik_tls_cert")
        self.assertEqual(certificate["keyFile"], "/run/secrets/tsw_traefik_tls_key")
        default_certificate = tls_data["tls"]["stores"]["default"]["defaultCertificate"]
        self.assertEqual(default_certificate["certFile"], "/run/secrets/tsw_traefik_tls_cert")
        self.assertEqual(default_certificate["keyFile"], "/run/secrets/tsw_traefik_tls_key")
        self.assertNotIn("BEGIN", tls_content)
        self.assertNotIn("PRIVATE KEY", tls_content)

        dashboard_router = tls_data["http"]["routers"]["traefik-dashboard"]
        self.assertEqual(dashboard_router["rule"], "Host(`traefik.tsw.local`)")
        self.assertEqual(dashboard_router["service"], "api@internal")
        self.assertEqual(dashboard_router["entryPoints"], ["websecure"])
        self.assertEqual(dashboard_router["middlewares"], ["traefik-dashboard-auth"])
        self.assertIn("tls", dashboard_router)
        dashboard_auth = tls_data["http"]["middlewares"]["traefik-dashboard-auth"]
        self.assertEqual(
            dashboard_auth["basicAuth"]["usersFile"],
            "/run/secrets/tsw_traefik_gui_users",
        )
        self.assertNotIn("users:", tls_content)
        self.assertNotIn("api.insecure", tls_content)

    def test_committed_service_stacks_define_traefik_swarm_route_labels(self):
        expected = {
            "infisical": ("infisical", "infisical.tsw.local", "8080"),
            "jenkins": ("jenkins", "jenkins.tsw.local", "8080"),
            "nexus": ("nexus", "nexus.tsw.local", "8081"),
            "portainer": ("portainer", "portainer.tsw.local", "9000"),
            "service-access": ("service-access-dashboard", "service-access.tsw.local", "80"),
            "sonarqube": ("sonarqube", "sonarqube.tsw.local", "9000"),
            "swagger": ("swagger-nginx", "swagger.tsw.local", "8084"),
        }
        repository = ComposeFileRepositoryYaml()

        for stack_name, (service_name, hostname, upstream_port) in expected.items():
            with self.subTest(stack_name=stack_name):
                stack_definition = repository.get_compose_of(stack_name)
                compose_data = YAML(typ="safe").load(stack_definition.compose_content)
                service = compose_data["services"][service_name]
                labels = set(service["deploy"]["labels"])

                self.assertIn("service_access_link", service["networks"])
                self.assertEqual(
                    compose_data["networks"]["service_access_link"],
                    {"name": "service_access_link", "external": True},
                )
                self.assertIn("traefik.enable=true", labels)
                self.assertIn("traefik.swarm.network=service_access_link", labels)
                router_name = service_name.removesuffix("-dashboard").removesuffix("-nginx")
                self.assertIn(
                    f"traefik.http.routers.{router_name}.rule=Host(`{hostname}`)",
                    labels,
                )
                self.assertNotIn("Host(`localhost`)", repr(labels))
                self.assertIn(
                    f"traefik.http.routers.{router_name}.entrypoints=websecure",
                    labels,
                )
                self.assertIn(f"traefik.http.routers.{router_name}.tls=true", labels)
                self.assertIn(
                    (
                        f"traefik.http.services.{router_name}"
                        f".loadbalancer.server.port={upstream_port}"
                    ),
                    labels,
                )

    def test_rendered_pulsar_bootstrap_command_remains_valid_python(self):
        stack_definition = ComposeFileRepositoryYaml().get_compose_of("pulsar")
        compose_data = YAML(typ="safe").load(stack_definition.compose_content)
        script = compose_data["services"]["pulsar-manager-bootstrap"]["command"][2]

        self.assertIn("traefik.http.routers.pulsar.rule=Host(`pulsar.tsw.local`)", stack_definition.compose_content)
        self.assertTrue(script.startswith("python - <<'PY'\n"))
        python_source = script.removeprefix("python - <<'PY'\n").rsplit("\nPY", maxsplit=1)[0]
        compile(python_source, "pulsar-manager-bootstrap", "exec")
        self.assertNotIn("\n import urllib.error", script)
        self.assertNotIn("\n for _ in range(180):", script)

    def test_committed_service_stack_route_labels_are_renderer_owned(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_root = repository_root / "infra" / "config" / "compose"

        for compose_path in sorted(compose_root.glob("*/docker-compose.yml")):
            if compose_path.parent.name == "traefik":
                continue
            with self.subTest(compose_path=compose_path.as_posix()):
                raw_compose = compose_path.read_text(encoding="utf-8")

                self.assertNotIn("traefik.enable=", raw_compose)
                self.assertNotIn("traefik.swarm.network=", raw_compose)
                self.assertNotIn("traefik.http.routers.", raw_compose)
                self.assertNotIn("traefik.http.services.", raw_compose)

    def test_service_access_dashboard_and_nginx_are_image_packaged(self):
        repository_root = Path(__file__).resolve().parents[4]
        compose_data = YAML(typ="safe").load(
            (
                repository_root / "infra" / "config" / "compose" / "service-access" / "docker-compose.yml"
            ).read_text(encoding="utf-8")
        )
        packaged_services = {
            "service-access-dashboard": (
                repository_root
                / "infra"
                / "config"
                / "compose"
                / "service-access"
                / "dashboard"
                / "Dockerfile",
                "COPY --chown=nginx:nginx index.html /usr/share/nginx/html/index.html",
                "FROM nginx:1.29.8-alpine",
            ),
            "service-access-nginx": (
                repository_root
                / "infra"
                / "config"
                / "compose"
                / "service-access"
                / "nginx"
                / "Dockerfile",
                "COPY --chown=nginx:nginx default.conf /etc/nginx/conf.d/default.conf",
                "FROM nginx:1.29.8-alpine",
            ),
        }

        for service_name, (dockerfile_path, copy_line, base_image_line) in packaged_services.items():
            with self.subTest(service_name=service_name):
                service = compose_data["services"][service_name]
                self.assertIn("image", service)
                self.assertNotIn("build", service)
                self.assertNotIn("volumes", service)
                if service_name == "service-access-dashboard":
                    self.assertEqual(
                        service["configs"],
                        [
                            {
                                "source": "service_access_dashboard_index",
                                "target": "/usr/share/nginx/html/index.html",
                            }
                        ],
                    )
                    self.assertEqual(
                        (
                            compose_data["configs"]["service_access_dashboard_index"]["file"]
                        ),
                        "${TSW_REMOTE_STACK_ROOT:-/var/lib/tiny-swarm-world/stacks}"
                            "/service-access/dashboard/index.html",
                    )
                else:
                    self.assertNotIn("configs", service)
                self.assertNotIn("secrets", service)
                self.assertTrue(dockerfile_path.is_file())
                dockerfile = dockerfile_path.read_text(encoding="utf-8")
                self.assertIn(base_image_line, dockerfile)
                self.assertIn(copy_line, dockerfile)
                self.assertIn("pid /tmp/nginx.pid", dockerfile)
                self.assertNotIn("apk add", dockerfile)
                self.assertNotIn("setcap", dockerfile)
                if service_name == "service-access-nginx":
                    self.assertNotIn("generate-self-signed-cert.sh", dockerfile)

    def test_service_access_image_publisher_packages_dashboard_and_nginx_assets(self):
        publisher = _CapturingImagePublisher()
        expected_archives = {
            "service-access-dashboard": {"Dockerfile", "index.html"},
            "service-access-nginx": {
                "Dockerfile",
                "default.conf",
                "generate-self-signed-cert.sh",
            },
        }

        for contract in DEFAULT_CONTAINER_IMAGE_CONTRACTS:
            if contract.build_context in expected_archives:
                with self.subTest(build_context=contract.build_context):
                    context_path = publisher._context_path(contract)
                    publisher._transfer_context(
                        context_path,
                        f"/remote/images/{contract.build_context}",
                    )
                    self.assertEqual(
                        expected_archives[contract.build_context],
                        publisher.archived_files[-1],
                    )

    def test_service_access_dashboard_exposes_management_table_columns(self):
        dashboard = _rendered_service_access_dashboard_html()

        for label in ("Service", "URL", "User", "Password"):
            with self.subTest(label=label):
                self.assertIn(f">{label}<", dashboard)

    def test_default_service_access_dashboard_matches_effective_access_model(self):
        repository = ComposeFileRepositoryYaml()

        dashboard, links = _assert_dashboard_matches_effective_access_model(
            self,
            repository,
        )
        rendered_services = {str(link["service"]) for link in links}

        self.assertEqual(set(CORE_ROUTE_EXPECTATIONS), rendered_services)
        for route_name in OPTIONAL_ROUTE_EXPECTATIONS:
            with self.subTest(route_name=route_name):
                self.assertNotIn(f"https://{OPTIONAL_ROUTE_EXPECTATIONS[route_name][1]}", dashboard)

    def test_enabled_optional_dashboard_links_follow_isolated_effective_model(self):
        optional_names = set(OPTIONAL_ROUTE_EXPECTATIONS)
        optional_urls = {
            route_name: f"https://{route_contract[1]}"
            for route_name, route_contract in OPTIONAL_ROUTE_EXPECTATIONS.items()
        }

        for enabled_route in OPTIONAL_ROUTE_EXPECTATIONS:
            with self.subTest(enabled_route=enabled_route):
                with effective_access_model_fixture(
                    enabled_services=(enabled_route,),
                ) as fixture:
                    dashboard, links = _assert_dashboard_matches_effective_access_model(
                        self,
                        fixture.repository,
                    )
                rendered_services = {str(link["service"]) for link in links}

                self.assertEqual(rendered_services & optional_names, {enabled_route})
                self.assertIn(optional_urls[enabled_route], dashboard)
                for disabled_route in optional_names - {enabled_route}:
                    self.assertNotIn(optional_urls[disabled_route], dashboard)

    def test_all_enabled_optionals_preserve_default_core_dashboard_links(self):
        default_repository = ComposeFileRepositoryYaml()
        _, default_links = _assert_dashboard_matches_effective_access_model(
            self,
            default_repository,
        )
        default_urls = {
            str(link["service"]): str(link["url"])
            for link in default_links
        }

        with effective_access_model_fixture(
            enabled_services=tuple(OPTIONAL_ROUTE_EXPECTATIONS),
        ) as fixture:
            dashboard, enabled_links = _assert_dashboard_matches_effective_access_model(
                self,
                fixture.repository,
            )
        enabled_urls = {
            str(link["service"]): str(link["url"])
            for link in enabled_links
        }

        self.assertEqual(set(OPTIONAL_ROUTE_EXPECTATIONS), set(enabled_urls) - set(default_urls))
        for route_name in CORE_ROUTE_EXPECTATIONS:
            with self.subTest(route_name=route_name):
                self.assertEqual(default_urls[route_name], enabled_urls[route_name])
        for route_name, route_contract in OPTIONAL_ROUTE_EXPECTATIONS.items():
            with self.subTest(route_name=route_name):
                self.assertEqual(enabled_urls[route_name], f"https://{route_contract[1]}")
                self.assertIn(enabled_urls[route_name], dashboard)

    def test_committed_service_access_dashboard_fallback_matches_default_renderer(self):
        committed_fallback = _committed_service_access_dashboard_html()
        rendered = _rendered_service_access_dashboard_html()

        self.assertEqual(rendered, committed_fallback)

    def test_service_access_dashboard_visible_text_is_english(self):
        dashboard = _rendered_service_access_dashboard_html()

        for expected in (
            "Management table for local Tiny Swarm World services and Infisical secret entries.",
            "Open Infisical",
            "Passwords are visible through Infisical",
            "Traefik routed access",
            "Open Infisical item",
            "Dashboard does not require a login",
            "Swagger/NGINX does not require a login",
            "This page does not store plaintext passwords.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, dashboard)
        for forbidden in (
            "Verwaltungstabelle",
            "oeffnen",
            "Passwoerter",
            "Lokales",
            "anzeigen",
            "selbst",
            "keinen Login",
            "Passwortwerte",
            "Klartext",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, dashboard)

    def test_service_access_dashboard_links_to_allocated_ports_without_credentials(self):
        repository = ComposeFileRepositoryYaml()
        dashboard = repository.render_service_access_dashboard()
        model_links = _effective_service_access_links(repository)
        links = _extract_links(dashboard)

        self.assertTrue(links)
        self.assertEqual({str(link["url"]) for link in model_links}, set(links))
        for link in links:
            parsed = urlparse(link)
            self.assertFalse(parsed.username)
            self.assertFalse(parsed.password)
            self.assertNotIn(parsed.port, {10080, 10443})
            self.assertEqual(parsed.query, "")
            self.assertEqual(parsed.fragment, "")
        for forbidden_link in (
            "http://localhost:8085",
            "http://localhost:10000/jenkins",
            "http://localhost:10000/nexus",
            "http://localhost:10000/portainer",
            "http://localhost:10000/pulsar",
            "http://localhost:10000/pulsar-admin-api",
            "http://localhost:10000/sonarqube",
            "http://localhost:10000/swagger",
        ):
            self.assertNotIn(forbidden_link, dashboard)

    def test_service_access_dashboard_displays_allocated_service_ports(self):
        dashboard = _rendered_service_access_dashboard_html()

        for expected in (
            "https://service-access.tsw.local",
            "https://portainer.tsw.local",
            "https://jenkins.tsw.local",
            "https://sonarqube.tsw.local",
            "https://nexus.tsw.local",
            "https://pulsar-api.tsw.local/admin/v2/clusters",
            "https://pulsar.tsw.local",
            "https://swagger.tsw.local",
            "https://infisical.tsw.local",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, dashboard)
        for stale_url in (
            "http://localhost/jenkins",
            "http://localhost/nexus",
            "http://localhost/portainer",
            "http://localhost/pulsar",
            "http://localhost/pulsar-admin-api",
            "http://localhost/sonarqube",
            "http://localhost/swagger",
        ):
            with self.subTest(stale_url=stale_url):
                self.assertNotIn(stale_url, dashboard)

    def test_service_access_dashboard_links_open_new_tabs_safely(self):
        dashboard = _rendered_service_access_dashboard_html()
        collector = _LinkCollector()
        collector.feed(dashboard)

        self.assertTrue(collector.link_attributes)
        for attributes in collector.link_attributes:
            with self.subTest(href=attributes.get("href")):
                self.assertEqual(attributes.get("target"), "_blank")
                rel_values = set((attributes.get("rel") or "").split())
                self.assertIn("noopener", rel_values)
                self.assertIn("noreferrer", rel_values)

    def test_service_access_dashboard_lists_credential_references_without_values(self):
        repository = ComposeFileRepositoryYaml()
        dashboard = repository.render_service_access_dashboard()
        links = _effective_service_access_links(repository)
        expected_items = (
            "platform/portainer",
            "platform/nexus",
            "platform/jenkins",
            "platform/pulsar",
            "platform/pulsar-manager",
            "platform/sonarqube",
            "platform/infisical",
        )

        for item in expected_items:
            with self.subTest(item=item):
                self.assertIn(f"<code>{item}</code>", dashboard)
        for link in links:
            credential = link.get("credential")
            if not isinstance(credential, dict):
                continue
            with self.subTest(service=link["service"]):
                self.assertIn(f'<code>{credential["username_label"]}</code>', dashboard)
                self.assertIn(f'<code>{credential["item_reference"]}</code>', dashboard)
        for forbidden in (
            "password=",
            "token=",
            "secret=",
            "api_key=",
            "access_token=",
            "Bearer ",
            "Basic ",
            "admin1234567890",
            "MyAdminPassWord1234-126354654",
            "admin" + "Password123",
        ):
            self.assertNotIn(forbidden, dashboard)

    def test_service_access_dashboard_ignores_non_allowlisted_secret_values(self):
        repository = ComposeFileRepositoryYaml()
        model = repository.get_effective_access_model().to_dict()
        links = cast(list[dict[str, Any]], model["service_access_links"])
        sentinel_values = (
            "slice-03-password-value",
            "slice-03-token-value",
            "-----BEGIN PRIVATE KEY-----slice-03-private-key-value",
        )
        for link in links:
            credential = link.get("credential")
            if isinstance(credential, dict):
                credential.update(
                    {
                        "password": sentinel_values[0],
                        "token": sentinel_values[1],
                        "private_key": sentinel_values[2],
                    }
                )

        with patch.object(repository, "get_effective_access_model") as get_model:
            get_model.return_value.to_dict.return_value = model
            dashboard = repository.render_service_access_dashboard()

        for sentinel_value in sentinel_values:
            self.assertNotIn(sentinel_value, dashboard)


class _LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.link_attributes: list[dict[str, str]] = []
        self.row_count = 0
        self.row_links: list[str] = []
        self._in_table_body = False
        self._row_link_captured = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody":
            self._in_table_body = True
            return
        if tag == "tr" and self._in_table_body:
            self.row_count += 1
            self._row_link_captured = False
        if tag != "a":
            return
        attributes = {key: value or "" for key, value in attrs}
        href = attributes.get("href")
        if href:
            self.links.append(href)
            self.link_attributes.append(attributes)
            if self._in_table_body and not self._row_link_captured:
                self.row_links.append(href)
                self._row_link_captured = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_table_body = False


def _extract_links(html: str) -> list[str]:
    collector = _LinkCollector()
    collector.feed(html)
    return collector.links


def _effective_service_access_links(
    repository: ComposeFileRepositoryYaml,
) -> tuple[dict[str, Any], ...]:
    model = repository.get_effective_access_model().to_dict()
    return tuple(cast(list[dict[str, Any]], model["service_access_links"]))


def _assert_dashboard_matches_effective_access_model(
    testcase: unittest.TestCase,
    repository: ComposeFileRepositoryYaml,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    dashboard = repository.render_service_access_dashboard()
    links = _effective_service_access_links(repository)
    collector = _LinkCollector()
    collector.feed(dashboard)

    testcase.assertEqual(len(links), collector.row_count)
    testcase.assertEqual(
        tuple(str(link["url"]) for link in links),
        tuple(collector.row_links),
    )
    for url in collector.row_links:
        parsed = urlparse(url)
        testcase.assertEqual("https", parsed.scheme)
        testcase.assertNotIn(parsed.port, {10080, 10443})

    return dashboard, links


def _rendered_service_access_dashboard_html() -> str:
    return ComposeFileRepositoryYaml().render_service_access_dashboard()


class _CapturingImagePublisher(LxcContainerImagePublisher):
    def __init__(self):
        super().__init__(
            backend=ManagedLxcBackend.LXD,
            registry_username="registry-user",
            registry_password="registry-password",
        )
        self.archived_files: list[set[str]] = []

    def _run_manager_shell_bytes(
        self,
        script: str,
        *,
        input_bytes: bytes,
        timeout_seconds: int,
    ):
        with tarfile.open(fileobj=BytesIO(input_bytes), mode="r") as archive:
            self.archived_files.append(set(archive.getnames()))


def _committed_service_access_dashboard_html() -> str:
    repository_root = Path(__file__).resolve().parents[4]
    return (
        repository_root
        / "infra"
        / "config"
        / "compose"
        / "service-access"
        / "dashboard"
        / "index.html"
    ).read_text(encoding="utf-8")
