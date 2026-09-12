from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from tiny_swarm_world.application.ports.update import PortUpdateStateStore
from tiny_swarm_world.domain.update import ClassicUpdatePlan, ClassicUpdateState


class JsonUpdateStateStore(PortUpdateStateStore):
    """Persist only non-secret update rollback metadata with private permissions."""

    def __init__(self, root: Path):
        self.root = root

    def save(self, plan: ClassicUpdatePlan) -> ClassicUpdateState:
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        state = ClassicUpdateState(plan=plan, recorded_at=datetime.now(UTC).isoformat())
        path = self._path(plan.stack_name, plan.service_name)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.root, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(
                    {"plan": plan.to_dict(), "recorded_at": state.recorded_at},
                    temporary,
                    indent=2,
                )
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return state

    def load(self, stack_name: str, service_name: str) -> ClassicUpdateState | None:
        path = self._path(stack_name, service_name)
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict) or not isinstance(
                payload.get("plan"), dict
            ):
                raise ValueError("Update state and plan must be objects.")
            plan_data = payload["plan"]
            plan_fields = {
                field: _required_text(plan_data[field])
                for field in (
                    "stack_name",
                    "service_name",
                    "source_image",
                    "target_image",
                )
            }
            recorded_at = _required_text(payload["recorded_at"])
            state = ClassicUpdateState(
                plan=ClassicUpdatePlan(**plan_fields),
                recorded_at=recorded_at,
            )
            if (
                state.plan.stack_name != stack_name
                or state.plan.service_name != service_name
            ):
                raise ValueError(
                    "Update state identity does not match its selected service."
                )
            return state
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Stored update state is invalid; preserve it for diagnosis."
            ) from exc

    def _path(self, stack_name: str, service_name: str) -> Path:
        if not all(
            re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", name)
            for name in (stack_name, service_name)
        ):
            raise ValueError("Invalid update state identity.")
        return self.root / f"{stack_name}__{service_name}.json"


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Update state fields must be nonempty strings.")
    return value
