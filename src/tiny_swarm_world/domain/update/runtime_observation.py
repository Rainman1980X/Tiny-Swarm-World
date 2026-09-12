from __future__ import annotations

from dataclasses import dataclass


def image_matches(observed: str, expected: str) -> bool:
    """Match a requested reference without discarding an explicitly pinned digest."""
    observed_name, _, observed_digest = observed.partition("@")
    expected_name, _, expected_digest = expected.partition("@")
    if expected_digest:
        return observed_digest == expected_digest and _repository(
            observed_name
        ) == _repository(expected_name)
    return observed_name == expected_name


def _repository(reference: str) -> str:
    prefix, separator, name = reference.rpartition("/")
    return prefix + separator + name.split(":", 1)[0]


@dataclass(frozen=True)
class UpdateTaskObservation:
    task_id: str
    image: str
    state: str
    desired_state: str

    @property
    def active(self) -> bool:
        return self.state == "running" or self.desired_state == "running"


@dataclass(frozen=True)
class UpdateRuntimeObservation:
    stack_name: str
    service_name: str
    service_id: str
    service_version: int
    desired_image: str
    desired_replicas: int
    tasks: tuple[UpdateTaskObservation, ...]
    rollout_state: str

    @property
    def active_tasks(self) -> tuple[UpdateTaskObservation, ...]:
        return tuple(task for task in self.tasks if task.active)

    @property
    def rollout_failed(self) -> bool:
        return self.rollout_state in {
            "paused",
            "rollback_started",
            "rollback_paused",
            "rollback_completed",
        }

    def converged(self, image: str, *, allow_completed_rollback: bool = False) -> bool:
        active = self.active_tasks
        digests = {task.image.partition("@")[2] for task in active}
        return (
            bool(self.service_id)
            and (
                self.rollout_state in {"", "completed"}
                or (
                    allow_completed_rollback
                    and self.rollout_state == "rollback_completed"
                )
            )
            and self.desired_replicas > 0
            and len(active) == self.desired_replicas
            and len({task.task_id for task in active}) == len(active)
            and len(digests) == 1
            and image_matches(self.desired_image, image)
            and all(
                task.task_id
                and task.state == "running"
                and task.desired_state == "running"
                and image_matches(task.image, self.desired_image)
                for task in active
            )
        )

    def belongs_to_transition(self, source: str, target: str) -> bool:
        """Recovery may repair mixed source/target tasks, never unrelated drift."""
        return (
            self.desired_replicas > 0
            and any(
                image_matches(self.desired_image, image) for image in (source, target)
            )
            and all(
                any(image_matches(task.image, image) for image in (source, target))
                for task in self.active_tasks
            )
        )

    def to_evidence(self) -> dict[str, str]:
        active = self.active_tasks
        return {
            "service_id": self.service_id,
            "service_version": str(self.service_version),
            "desired_image": self.desired_image,
            "desired_replicas": str(self.desired_replicas),
            "running_tasks": str(sum(task.state == "running" for task in active)),
            "active_task_images": ",".join(sorted({task.image for task in active})),
            "rollout_state": self.rollout_state or "not_started",
        }
