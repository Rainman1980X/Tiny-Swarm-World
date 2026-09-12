from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tiny_swarm_world.domain.update import ClassicUpdatePlan
from tiny_swarm_world.infrastructure.adapters.update import JsonUpdateStateStore


class JsonUpdateStateStoreTest(unittest.TestCase):
    def test_round_trip_persists_only_update_metadata_with_private_file(self) -> None:
        with TemporaryDirectory() as directory:
            store = JsonUpdateStateStore(Path(directory) / "updates")
            plan = ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")

            saved = store.save(plan)
            loaded = store.load("jenkins", "jenkins")

            if loaded is None:
                self.fail("saved update state could not be loaded")
            self.assertEqual(plan, loaded.plan)
            self.assertEqual(0o700, (Path(directory) / "updates").stat().st_mode & 0o777)
            self.assertEqual(0o600, (Path(directory) / "updates/jenkins__jenkins.json").stat().st_mode & 0o777)
            self.assertEqual(plan, saved.plan)
