from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import Mock

from tiny_swarm_world.application.ports.update import UpdateObservationError
from tiny_swarm_world.domain.node_provider import ManagedLxcBackend
from tiny_swarm_world.infrastructure.adapters.clients.lxc.command.manager_shell_gateway import (
    LxcManagerShellGateway,
)
from tiny_swarm_world.infrastructure.adapters.update.lxc_runtime_observer import (
    LxcUpdateRuntimeObserver,
)


def _service(**changes):
    return {
        "id": "service-id",
        "version": 10,
        "name": "jenkins_jenkins",
        "image": "jenkins:2",
        "mode": {"Replicated": {"Replicas": 1}},
        "rollout": "completed",
        **changes,
    }


def _task(**changes):
    return {
        "id": "task-id",
        "image": "jenkins:2",
        "state": "Running 2 minutes ago",
        "desired_state": "Running",
        **changes,
    }


def _result(payload):
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def _observer(*, service=None, tasks=None, after=None):
    service = service if service is not None else _service()
    gateway = Mock(spec=LxcManagerShellGateway)
    gateway.run_manager_shell.side_effect = [
        _result(service),
        subprocess.CompletedProcess(
            [], 0, "\n".join(json.dumps(task) for task in (tasks or [_task()])), ""
        ),
        _result(after if after is not None else service),
    ]
    return LxcUpdateRuntimeObserver(gateway), gateway


class LxcUpdateRuntimeObserverTest(unittest.IsolatedAsyncioTestCase):
    async def test_observes_active_and_historical_task_states_without_mutation(self):
        observer, gateway = _observer(
            tasks=[
                _task(),
                _task(
                    id="old",
                    image="jenkins:1",
                    state="Shutdown 1 minute ago",
                    desired_state="Shutdown",
                ),
            ]
        )
        result = await observer.observe("jenkins", "jenkins")
        self.assertEqual("service-id", result.service_id)
        self.assertEqual(10, result.service_version)
        self.assertEqual(2, len(result.tasks))
        self.assertTrue(result.converged("jenkins:2"))
        commands = [call.args[0] for call in gateway.run_manager_shell.call_args_list]
        self.assertEqual(3, len(commands))
        self.assertTrue(commands[0].startswith("docker service inspect --format "))
        self.assertTrue(
            commands[1].startswith("docker service ps --no-trunc --format ")
        )
        self.assertEqual(commands[0], commands[2])
        for command in commands:
            self.assertNotIn("{{json .}}", command)
            self.assertNotIn(".Env", command)
            self.assertNotIn(".Error", command)
            self.assertNotIn(" update ", command)
            self.assertNotIn(" deploy ", command)

    async def test_running_old_task_is_retained_until_it_stops(self):
        observer, _ = _observer(
            tasks=[
                _task(),
                _task(id="old", image="jenkins:1", desired_state="Shutdown"),
            ]
        )
        result = await observer.observe("jenkins", "jenkins")
        self.assertEqual(2, len(result.active_tasks))
        self.assertFalse(result.converged("jenkins:2"))

    async def test_missing_malformed_unsupported_and_inconsistent_service_fail_closed(
        self,
    ):
        for service, after in (
            ([], None),
            (_service(mode={"Global": {}}), None),
            (_service(mode={"Replicated": {"Replicas": True}}), None),
            (_service(name="another_service"), None),
            (_service(), _service(version=11)),
            (_service(), _service(id="replacement")),
            (_service(image=None), None),
        ):
            with self.subTest(service=service, after=after):
                observer, _ = _observer(service=service, after=after)
                with self.assertRaises(UpdateObservationError):
                    await observer.observe("jenkins", "jenkins")

    async def test_malformed_task_fails_closed(self):
        for task in ({}, _task(state=None), _task(state=" \t "), _task(id="")):
            with self.subTest(task=task):
                observer, _ = _observer(tasks=[task])
                with self.assertRaises(UpdateObservationError):
                    await observer.observe("jenkins", "jenkins")

    async def test_unknown_task_states_fail_closed(self):
        for state, desired_state in (
            ("InvalidState", "InvalidState"),
            ("InvalidState 1 minute ago", "Shutdown"),
            ("Shutdown 1 minute ago", "InvalidState"),
        ):
            with self.subTest(state=state, desired_state=desired_state):
                observer, _ = _observer(
                    tasks=[
                        _task(),
                        _task(
                            id="unknown-task",
                            image="unrelated:9",
                            state=state,
                            desired_state=desired_state,
                        ),
                    ]
                )
                with self.assertRaises(UpdateObservationError):
                    await observer.observe("jenkins", "jenkins")

    async def test_recognized_terminal_history_is_preserved(self):
        for state in (
            "Complete",
            "Shutdown",
            "Failed",
            "Rejected",
            "Remove",
            "Orphaned",
        ):
            with self.subTest(state=state):
                observer, _ = _observer(
                    tasks=[
                        _task(),
                        _task(
                            id="history",
                            image="old:1",
                            state=state + " 1 minute ago",
                            desired_state="Shutdown",
                        ),
                    ]
                )
                observed = await observer.observe("jenkins", "jenkins")
                self.assertEqual(2, len(observed.tasks))
                self.assertTrue(observed.converged("jenkins:2"))

    async def test_recognized_pending_tasks_do_not_converge(self):
        for state in (
            "New",
            "Allocated",
            "Pending",
            "Assigned",
            "Accepted",
            "Preparing",
            "Ready",
            "Starting",
        ):
            with self.subTest(state=state):
                observer, _ = _observer(tasks=[_task(state=state + " 1 second ago")])
                observed = await observer.observe("jenkins", "jenkins")
                self.assertFalse(observed.converged("jenkins:2"))

    async def test_command_errors_and_invalid_json_do_not_escape_as_success(self):
        for result in (
            subprocess.CompletedProcess([], 1, "", "raw-private-output"),
            subprocess.CompletedProcess([], 0, "not JSON", ""),
        ):
            with self.subTest(returncode=result.returncode):
                observer, gateway = _observer()
                gateway.run_manager_shell.side_effect = [result]
                with self.assertRaises(UpdateObservationError) as caught:
                    await observer.observe("jenkins", "jenkins")
                self.assertNotIn("raw-private-output", str(caught.exception))

    async def test_invalid_identity_never_reaches_command_runner(self):
        observer, gateway = _observer()
        for value in ("bad;command", "../path", "-option"):
            with self.subTest(value=value), self.assertRaises(UpdateObservationError):
                await observer.observe(value, "jenkins")
        gateway.run_manager_shell.assert_not_called()

    async def test_reuses_incus_manager_route_with_mocked_process_runner(self):
        runner = Mock()
        runner.run_text.side_effect = [
            _result(_service()),
            _result(_task()),
            _result(_service()),
        ]
        gateway = LxcManagerShellGateway(
            backend=ManagedLxcBackend.INCUS,
            manager_node="swarm-manager",
            timeout_seconds=10,
            logger=Mock(),
            process_runner=runner,
        )
        observer = LxcUpdateRuntimeObserver(gateway)
        runner.run_text.assert_not_called()
        result = await observer.observe("jenkins", "jenkins")
        self.assertTrue(result.converged("jenkins:2"))
        for call in runner.run_text.call_args_list:
            self.assertEqual(
                ["incus", "exec", "swarm-manager", "--", "sh", "-lc"], call.args[0][:6]
            )
            self.assertEqual(10, call.kwargs["timeout"])
            self.assertFalse(call.kwargs["shell"])
