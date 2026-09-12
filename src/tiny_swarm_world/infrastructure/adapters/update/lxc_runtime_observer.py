from __future__ import annotations

import asyncio
import json
import re
import shlex
from collections.abc import Mapping

from tiny_swarm_world.application.ports.update import (
    PortUpdateRuntimeObserver,
    UpdateObservationError,
    UpdateObservationChanged,
)
from tiny_swarm_world.domain.update import (
    UpdateRuntimeObservation,
    UpdateTaskObservation,
)
from tiny_swarm_world.infrastructure.adapters.clients.lxc.command.manager_shell_gateway import (
    LxcManagerShellGateway,
)


_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
# Docker Engine TaskState values apply to both current and desired task state.
_TASK_STATES = frozenset(
    {
        "new",
        "allocated",
        "pending",
        "assigned",
        "accepted",
        "preparing",
        "ready",
        "starting",
        "running",
        "complete",
        "shutdown",
        "failed",
        "rejected",
        "remove",
        "orphaned",
    }
)
# Project only public identity/rollout fields: the gateway logs command output.
_SERVICE_FORMAT = (
    '{"id":{{json .ID}},"version":{{json .Version.Index}},'
    '"name":{{json .Spec.Name}},"image":{{json .Spec.TaskTemplate.ContainerSpec.Image}},'
    '"mode":{{json .Spec.Mode}},'
    '"rollout":{{if .UpdateStatus}}{{json .UpdateStatus.State}}{{else}}""{{end}}}'
)
_TASK_FORMAT = (
    '{"id":{{json .ID}},"image":{{json .Image}},'
    '"state":{{json .CurrentState}},"desired_state":{{json .DesiredState}}}'
)


class LxcUpdateRuntimeObserver(PortUpdateRuntimeObserver):
    """Observe Swarm service/task state through the existing managed-node route."""

    def __init__(self, gateway: LxcManagerShellGateway) -> None:
        self.gateway = gateway

    async def observe(
        self, stack_name: str, service_name: str
    ) -> UpdateRuntimeObservation:
        if not all(_IDENTIFIER.fullmatch(name) for name in (stack_name, service_name)):
            raise UpdateObservationError("invalid_service_identity")
        try:
            return await asyncio.to_thread(self._observe, stack_name, service_name)
        except UpdateObservationChanged:
            raise
        except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            # Do not propagate raw command output or parser inputs into evidence.
            raise UpdateObservationError("runtime_observation_unavailable") from exc

    def _observe(self, stack_name: str, service_name: str) -> UpdateRuntimeObservation:
        service = f"{stack_name}_{service_name}"
        inspect_command = (
            f"docker service inspect --format {shlex.quote(_SERVICE_FORMAT)} "
            f"-- {shlex.quote(service)}"
        )
        before = _mapping(json.loads(self._read(inspect_command)))
        task_output = self._read(
            f"docker service ps --no-trunc --format {shlex.quote(_TASK_FORMAT)} "
            f"-- {shlex.quote(service)}"
        )
        after = _mapping(json.loads(self._read(inspect_command)))
        if (
            _text(before, "name") != service
            or _text(after, "name") != service
            or _text(before, "id") != _text(after, "id")
        ):
            raise ValueError("service_identity_changed_during_observation")
        for record in (before, after):
            _number(record, "version")
            _text(record, "image")
            _text(record, "rollout", allow_empty=True)
            _number(_mapping(_mapping(record["mode"])["Replicated"]), "Replicas")
        mode = _mapping(before["mode"])
        replicated = _mapping(mode["Replicated"])
        tasks = tuple(
            _task(json.loads(line)) for line in task_output.splitlines() if line.strip()
        )
        if before != after:
            raise UpdateObservationChanged("service_changed_during_observation")
        return UpdateRuntimeObservation(
            stack_name=stack_name,
            service_name=service_name,
            service_id=_text(before, "id"),
            service_version=_number(before, "version"),
            desired_image=_text(before, "image"),
            desired_replicas=_number(replicated, "Replicas"),
            tasks=tasks,
            rollout_state=_text(before, "rollout", allow_empty=True),
        )

    def _read(self, command: str) -> str:
        result = self.gateway.run_manager_shell(command, check=False)
        if result.returncode != 0:
            raise UpdateObservationError("runtime_command_failed")
        return result.stdout


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("invalid_runtime_record")
    return value


def _text(record: Mapping[str, object], key: str, *, allow_empty: bool = False) -> str:
    value = record[key]
    if not isinstance(value, str) or (not value.strip() and not allow_empty):
        raise ValueError("invalid_runtime_text")
    return value


def _number(record: Mapping[str, object], key: str) -> int:
    value = record[key]
    if type(value) is not int or value < 0:
        raise ValueError("invalid_runtime_number")
    return value


def _task(value: object) -> UpdateTaskObservation:
    record = _mapping(value)
    state = _text(record, "state").split()[0].lower()
    desired_state = _text(record, "desired_state").lower()
    if state not in _TASK_STATES or desired_state not in _TASK_STATES:
        raise ValueError("unknown_runtime_task_state")
    return UpdateTaskObservation(
        task_id=_text(record, "id"),
        image=_text(record, "image"),
        state=state,
        desired_state=desired_state,
    )
