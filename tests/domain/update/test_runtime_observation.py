from dataclasses import replace
import unittest

from tiny_swarm_world.domain.update import (
    UpdateRuntimeObservation,
    UpdateTaskObservation,
    image_matches,
)


class UpdateRuntimeObservationTest(unittest.TestCase):
    def observation(self, image="repo:1"):
        return UpdateRuntimeObservation(
            "stack",
            "service",
            "identity",
            1,
            image,
            1,
            (UpdateTaskObservation("task", image, "running", "running"),),
            "completed",
        )

    def test_tag_accepts_resolved_reference_but_explicit_digest_must_match(self):
        digest = "sha256:" + "a" * 64
        other = "sha256:" + "b" * 64
        self.assertTrue(image_matches("repo:1@" + digest, "repo:1"))
        self.assertTrue(image_matches("repo:1@" + digest, "repo@" + digest))
        self.assertFalse(image_matches("repo:1@" + other, "repo:1@" + digest))
        self.assertFalse(image_matches("repo:1", "repo@" + digest))
        self.assertFalse(image_matches("other:1@" + digest, "repo@" + digest))

    def test_different_tags_for_same_content_are_not_rejected(self):
        digest = "@sha256:" + "a" * 64
        observation = replace(
            self.observation("repo:2" + digest),
            tasks=(
                UpdateTaskObservation("task", "repo:1" + digest, "running", "running"),
            ),
        )
        self.assertTrue(observation.converged("repo:2"))

    def test_historical_stopped_tasks_do_not_block_convergence(self):
        observation = self.observation()
        history = UpdateTaskObservation("history", "old:1", "shutdown", "shutdown")
        self.assertTrue(
            replace(observation, tasks=(*observation.tasks, history)).converged(
                "repo:1"
            )
        )

    def test_old_running_task_scheduled_for_shutdown_still_blocks(self):
        observation = self.observation()
        old = UpdateTaskObservation("old", "old:1", "running", "shutdown")
        self.assertFalse(
            replace(observation, tasks=(*observation.tasks, old)).converged("repo:1")
        )

    def test_zero_empty_duplicate_or_pending_tasks_never_pass(self):
        observation = self.observation()
        for candidate in (
            replace(observation, desired_replicas=0, tasks=()),
            replace(observation, tasks=()),
            replace(observation, desired_replicas=2, tasks=observation.tasks * 2),
            replace(
                observation, tasks=(replace(observation.tasks[0], state="starting"),)
            ),
            replace(observation, rollout_state="unknown"),
        ):
            with self.subTest(candidate=candidate):
                self.assertFalse(candidate.converged("repo:1"))

    def test_same_tag_with_different_active_digests_does_not_converge(self):
        observation = replace(
            self.observation(),
            desired_replicas=2,
            tasks=tuple(
                UpdateTaskObservation(
                    letter, "repo:1@sha256:" + letter * 64, "running", "running"
                )
                for letter in ("a", "b")
            ),
        )
        self.assertFalse(observation.converged("repo:1"))
