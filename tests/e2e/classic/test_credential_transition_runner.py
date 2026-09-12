"""Safety checks for the explicitly opt-in credential transition runner."""
import copy
import json
import unittest
from typing import Any

from tests.e2e.classic.run_credential_transition_live import (
    comparable,
    deployment_source,
    require_persistent_jenkins_home,
)


class CredentialTransitionRunnerTest(unittest.TestCase):
    def test_source_evidence_requires_verified_unique_jenkins_result(self) -> None:
        entry = {"target_id": "deployment:jenkins-stack", "status": "verified",
                 "evidence": {"resolved_sources": "vault"}}
        self.assertEqual(deployment_source(json.dumps({"verification_results": [entry]}).encode()), "vault")
        for entries in ([{**entry, "status": "failed"}], [entry, entry],
                        [{**entry, "target_id": "deployment:other-stack"}],
                        [{**entry, "evidence": {"resolved_sources": "untrusted-value"}}]):
            with self.subTest(entries=entries):
                self.assertIsNone(deployment_source(json.dumps({"verification_results": entries}).encode()))
        self.assertIsNone(deployment_source(b"not-json"))

    def test_unmigrated_jenkins_home_is_rejected(self) -> None:
        snapshot: dict[str, Any] = {"jenkins_jenkins": {"TaskTemplate": {"ContainerSpec": {"Mounts": [
            {"Type": "volume", "Source": "jenkins_jenkins_home", "Target": "/var/lib/jenkins"},
        ]}}}}
        with self.assertRaisesRegex(RuntimeError, "jenkins_home_migration_required"):
            require_persistent_jenkins_home(snapshot)

    def test_named_volume_at_actual_home_is_accepted(self) -> None:
        require_persistent_jenkins_home({"jenkins_jenkins": {"TaskTemplate": {"ContainerSpec": {"Mounts": [
            {"Type": "volume", "Source": "jenkins_jenkins_home", "Target": "/var/jenkins_home"},
        ]}}}})

    def test_restart_comparison_preserves_unrelated_drift_and_input(self) -> None:
        snapshot: dict[str, Any] = {
            "jenkins_jenkins": {"TaskTemplate": {"ForceUpdate": 1, "ContainerSpec": {"Env": ["NAME=value"]}}},
            "other": {"TaskTemplate": {"ForceUpdate": 2}},
        }
        original = copy.deepcopy(snapshot)
        result = comparable(snapshot)
        self.assertEqual(snapshot, original)
        self.assertNotIn("ForceUpdate", result["jenkins_jenkins"]["TaskTemplate"])
        self.assertEqual(result["other"], original["other"])
        self.assertEqual(result["jenkins_jenkins"]["TaskTemplate"]["ContainerSpec"],
                         original["jenkins_jenkins"]["TaskTemplate"]["ContainerSpec"])
