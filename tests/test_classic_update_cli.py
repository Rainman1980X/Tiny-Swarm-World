from __future__ import annotations

import unittest

from tiny_swarm_world.__main__ import parse_args


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
