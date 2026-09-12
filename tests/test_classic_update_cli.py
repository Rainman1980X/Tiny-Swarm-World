from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tiny_swarm_world.__main__ import (
    _live_consent_for_workflow,
    parse_args,
    run_cli_workflow,
)
from tiny_swarm_world.domain.update import ClassicUpdatePlan


class ClassicUpdateCliTest(unittest.TestCase):
    def test_update_requires_explicit_transition_arguments(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["platform", "update"])

    def test_update_arguments_are_available_for_preview(self) -> None:
        args = parse_args(
            [
                "platform",
                "update",
                "--stack",
                "jenkins",
                "--service",
                "jenkins",
                "--from-image",
                "old:1",
                "--to-image",
                "new:1",
                "--preview",
            ]
        )

        self.assertTrue(args.preview)
        self.assertEqual("jenkins", args.stack)
        self.assertEqual("old:1", args.from_image)

    def test_update_options_are_rejected_for_other_workflows(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["platform", "verify", "--preview"])

    def test_recovery_requires_only_stack_and_service(self) -> None:
        args = parse_args(
            ["platform", "update", "--recover", "--stack", "jenkins", "--service", "jenkins"]
        )

        self.assertTrue(args.recover)
        self.assertIsNone(args.from_image)
        self.assertIsNone(args.to_image)

    def test_recovery_rejects_explicit_transition_images(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(
                [
                    "platform",
                    "update",
                    "--recover",
                    "--stack",
                    "jenkins",
                    "--service",
                    "jenkins",
                    "--from-image",
                    "old:1",
                    "--to-image",
                    "new:1",
                ]
            )

    def test_update_preview_does_not_require_live_consent(self) -> None:
        args = parse_args(
            [
                "platform",
                "update",
                "--stack",
                "jenkins",
                "--service",
                "jenkins",
                "--from-image",
                "old:1",
                "--to-image",
                "new:1",
                "--preview",
            ]
        )

        self.assertIsNone(_live_consent_for_workflow(args.workflow, args))

    def test_update_plan_is_built_from_transition_arguments(self) -> None:
        args = parse_args(
            [
                "platform",
                "update",
                "--stack",
                "jenkins",
                "--service",
                "jenkins",
                "--from-image",
                "old:1",
                "--to-image",
                "new:1",
            ]
        )

        from tiny_swarm_world.__main__ import _update_plan_from_args

        self.assertEqual(
            ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1"),
            _update_plan_from_args(args),
        )


class ClassicUpdateCliWorkflowTest(unittest.IsolatedAsyncioTestCase):
    def _workflow(self):
        return parse_args(
            [
                "platform",
                "update",
                "--stack",
                "jenkins",
                "--service",
                "jenkins",
                "--from-image",
                "old:1",
                "--to-image",
                "new:1",
            ]
        ).workflow

    async def test_update_apply_delegates_to_update_workflow(self) -> None:
        update_workflow = SimpleNamespace(run=AsyncMock(return_value="applied"))

        with patch(
            "tiny_swarm_world.__main__.build_classic_update_workflow",
            return_value=update_workflow,
        ) as build_workflow:
            result = await run_cli_workflow(
                self._workflow(),
                confirmation=None,
                update_plan=ClassicUpdatePlan("jenkins", "jenkins", "old:1", "new:1"),
                update_preview=False,
            )

        self.assertEqual("applied", result)
        build_workflow.assert_called_once()
        update_workflow.run.assert_awaited_once()

    async def test_update_recovery_delegates_to_update_workflow(self) -> None:
        update_workflow = SimpleNamespace(recover=AsyncMock(return_value="recovered"))

        with patch(
            "tiny_swarm_world.__main__.build_classic_update_workflow",
            return_value=update_workflow,
        ):
            result = await run_cli_workflow(
                self._workflow(),
                confirmation=None,
                update_recover=True,
                update_preview=True,
                update_stack_name="jenkins",
                update_service_name="jenkins",
            )

        self.assertEqual("recovered", result)
        update_workflow.recover.assert_awaited_once_with(
            "jenkins",
            "jenkins",
            preview=True,
            live_consent=None,
        )
