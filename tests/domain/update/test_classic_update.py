from __future__ import annotations

import unittest

from tiny_swarm_world.domain.update import (
    ClassicUpdatePlan,
    image_override_environment_name,
)


class ClassicUpdatePlanTest(unittest.TestCase):
    def test_plan_normalizes_safe_values_and_exposes_stable_target(self) -> None:
        plan = ClassicUpdatePlan(" jenkins ", " jenkins ", "old:1 ", " new:1 ")

        self.assertEqual("jenkins", plan.stack_name)
        self.assertEqual("jenkins", plan.service_name)
        self.assertEqual("update:jenkins:jenkins", plan.target_id)
        self.assertEqual("TSW_JENKINS_IMAGE", image_override_environment_name("jenkins", "jenkins"))

    def test_plan_rejects_same_image_and_shell_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "must differ"):
            ClassicUpdatePlan("jenkins", "jenkins", "same:1", "same:1")
        with self.assertRaisesRegex(ValueError, "safe image reference"):
            ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1;rm")

    def test_unsupported_stack_service_pair_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported"):
            image_override_environment_name("swagger", "swagger-ui")

    def test_plan_exposes_reversible_rollback_transition(self) -> None:
        plan = ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1")

        self.assertEqual("new:1", plan.rollback_plan.source_image)
        self.assertEqual("old:1", plan.rollback_plan.target_image)
