from __future__ import annotations

import os
import platform
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path


CI_ENVIRONMENT_KEYS = frozenset(
    ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "TF_BUILD")
)
VERIFIED_LIVE_RUNNER_ENVIRONMENT_KEY = "TSW_LIVE_RUNNER_VERIFIED"
CONTAINER_MARKER_FILES = (
    (".dockerenv",),
    ("run", ".containerenv"),
    ("var", "run", ".containerenv"),
)
CONTAINER_CGROUP_MARKERS = (
    "docker",
    "kubepods",
    "containerd",
    "libpod",
    "podman",
    "lxc",
)


@dataclass(frozen=True)
class LinuxHostSignals:
    platform_family: str
    distribution: str
    kernel_release: str
    proc_version: str
    sandbox_signal: str


class LinuxHostSignalReader:
    """Read Linux-family and sandbox facts without executing commands."""

    def __init__(
        self,
        *,
        os_root: Path = Path("/"),
        environment: Mapping[str, str] | None = None,
        platform_system: Callable[[], str] | None = None,
    ) -> None:
        self.os_root = os_root
        self.environment = os.environ if environment is None else environment
        self.platform_system = platform_system or platform.system

    def read(self) -> LinuxHostSignals:
        return LinuxHostSignals(
            platform_family=self.platform_system(),
            distribution=_distribution_from_os_release(
                _read_text(self.os_root / "etc" / "os-release")
            ),
            kernel_release=_first_line(
                _read_text(
                    self.os_root / "proc" / "sys" / "kernel" / "osrelease"
                )
            ),
            proc_version=_read_text(self.os_root / "proc" / "version"),
            sandbox_signal=self._sandbox_signal(),
        )

    def _sandbox_signal(self) -> str:
        if any(_exists(self.os_root.joinpath(*parts)) for parts in CONTAINER_MARKER_FILES):
            return "container_marker"
        cgroup_text = "\n".join(
            _read_text(self.os_root.joinpath(*parts)).casefold()
            for parts in (("proc", "1", "cgroup"), ("proc", "self", "cgroup"))
        )
        if any(marker in cgroup_text for marker in CONTAINER_CGROUP_MARKERS):
            return "container_marker"
        if self._ci_environment_is_unverified():
            return "ci_marker"
        return ""

    def _ci_environment_is_unverified(self) -> bool:
        return bool(
            any(self.environment.get(key) for key in CI_ENVIRONMENT_KEYS)
            and self.environment.get(VERIFIED_LIVE_RUNNER_ENVIRONMENT_KEY, "")
            .strip()
            .casefold()
            not in {"1", "true"}
        )


def _distribution_from_os_release(text: str) -> str:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in {"PRETTY_NAME", "NAME", "ID"}:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values.get("PRETTY_NAME") or values.get("NAME") or values.get("ID", "")


def _first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text.splitlines() else ""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False
