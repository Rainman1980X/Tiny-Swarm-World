from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

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
        path.write_text(
            json.dumps({"plan": plan.to_dict(), "recorded_at": state.recorded_at}, indent=2) + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
        return state

    def load(self, stack_name: str, service_name: str) -> ClassicUpdateState | None:
        path = self._path(stack_name, service_name)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            plan_data = payload["plan"]
            return ClassicUpdateState(
                plan=ClassicUpdatePlan(
                    stack_name=str(plan_data["stack_name"]),
                    service_name=str(plan_data["service_name"]),
                    source_image=str(plan_data["source_image"]),
                    target_image=str(plan_data["target_image"]),
                ),
                recorded_at=str(payload["recorded_at"]),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _path(self, stack_name: str, service_name: str) -> Path:
        return self.root / f"{stack_name}__{service_name}.json"
