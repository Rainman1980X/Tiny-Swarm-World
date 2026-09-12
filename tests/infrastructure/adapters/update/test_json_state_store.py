from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from tests.application.services.platform.test_classic_update_workflow import (
    _consent,
    _plan,
    _workflow,
)
from tiny_swarm_world.domain.update import ClassicUpdatePlan
from tiny_swarm_world.infrastructure.adapters.update import JsonUpdateStateStore


class JsonUpdateStateStoreTest(unittest.TestCase):
    def test_null_source_state_is_rejected(self) -> None:
        for field, value, payload in _invalid_records():
            with (
                self.subTest(field=field, value=value),
                TemporaryDirectory() as directory,
            ):
                path = Path(directory) / "jenkins__jenkins.json"
                content = json.dumps(payload)
                path.write_text(content, encoding="utf-8")
                store = JsonUpdateStateStore(Path(directory))
                with self.assertRaises(ValueError):
                    store.load("jenkins", "jenkins")
                self.assertEqual(content, path.read_text(encoding="utf-8"))

    def test_round_trip_persists_only_update_metadata_with_private_file(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory) / "updates")
            plan = ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")

            saved = store.save(plan)
            loaded = store.load("jenkins", "jenkins")

            if loaded is None:
                self.fail("saved update state could not be loaded")
            self.assertEqual(plan, loaded.plan)
            self.assertEqual(
                0o700, (Path(directory) / "updates").stat().st_mode & 0o777
            )
            self.assertEqual(
                0o600,
                (Path(directory) / "updates/jenkins__jenkins.json").stat().st_mode
                & 0o777,
            )
            self.assertEqual(plan, saved.plan)

    def test_load_returns_none_for_missing_state(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory) / "updates")

            self.assertIsNone(store.load("jenkins", "jenkins"))

    def test_load_rejects_malformed_state_instead_of_treating_it_as_missing(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "updates"
            root.mkdir()
            (root / "jenkins__jenkins.json").write_text("{malformed", encoding="utf-8")
            store = JsonUpdateStateStore(root)

            with self.assertRaises(ValueError):
                store.load("jenkins", "jenkins")
            self.assertEqual(
                "{malformed",
                (root / "jenkins__jenkins.json").read_text(encoding="utf-8"),
            )

    def test_failed_atomic_replace_preserves_previous_plan(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory) / "updates")
            plan = ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")
            store.save(plan)
            with patch(
                "tiny_swarm_world.infrastructure.adapters.update.json_state_store.os.replace",
                side_effect=OSError("disk failure"),
            ):
                with self.assertRaises(OSError):
                    store.save(plan.rollback_plan)
            state = store.load("jenkins", "jenkins")
            self.assertIsNotNone(state)
            self.assertEqual(plan, state.plan if state else None)
            self.assertEqual(
                ["jenkins__jenkins.json"], [path.name for path in store.root.iterdir()]
            )

    def test_load_rejects_mismatched_identity(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory) / "updates")
            store.save(ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1"))
            (store.root / "jenkins__jenkins.json").rename(
                store.root / "other__service.json"
            )
            with self.assertRaises(ValueError):
                store.load("other", "service")

    def test_load_rejects_path_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory))
            with self.assertRaises(ValueError):
                store.load("../outside", "service")


class CorruptUpdateStateRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_corrupt_state_never_reaches_recovery_deployment(self) -> None:
        for field, value, payload in _invalid_records():
            with (
                self.subTest(field=field, value=value),
                TemporaryDirectory() as directory,
            ):
                path = Path(directory) / "jenkins__jenkins.json"
                content = json.dumps(payload)
                path.write_text(content, encoding="utf-8")
                workflow, factory, _, _ = _workflow(initial="new:1", target="None")
                workflow.state_store = JsonUpdateStateStore(Path(directory))
                result = await workflow.recover(
                    "jenkins", "jenkins", preview=False, live_consent=_consent()
                )
                self.assertEqual("blocked", result.status.value)
                self.assertFalse(result.executed)
                factory.assert_not_called()
                workflow.runtime_observer.observe.assert_not_awaited()
                self.assertEqual(content, path.read_text(encoding="utf-8"))


def _invalid_records():
    for field in (
        "stack_name",
        "service_name",
        "source_image",
        "target_image",
        "recorded_at",
    ):
        for value in (None, 7, 1.5, True, [], {}, "", " \t "):
            payload = {
                "plan": _plan().to_dict(),
                "recorded_at": "2026-09-13T12:00:00+00:00",
            }
            target = payload if field == "recorded_at" else payload["plan"]
            target[field] = value
            yield field, value, payload
