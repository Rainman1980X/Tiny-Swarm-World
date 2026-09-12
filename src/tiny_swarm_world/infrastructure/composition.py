"""Public composition facade for Tiny Swarm World.

The concrete infrastructure wiring lives in focused internal composition
modules. This facade deliberately keeps the established import path stable for
the CLI, integrations, and compatibility tests while avoiding configuration,
probing, and runtime-construction details here.
"""

from __future__ import annotations

import importlib
import sys
from types import FunctionType
from typing import Any

from . import composition_runtime as _runtime


_RUNTIME_BUILDER_NAMES = (
    "build_application_logger",
    "build_host_environment_detector",
    "build_host_detection_service",
    "build_host_preparation_service",
    "build_project_filesystem_inspector",
    "build_preflight_service",
    "build_configuration_validation_service",
    "build_compose_file_repository",
    "build_network_doctor_service",
    "build_read_only_hang_diagnostics",
    "build_preflight_evidence_writer",
    "build_process_runner",
    "build_network_repair_service",
    "build_network_repair_options",
    "build_post_install_preflight_service",
    "build_setup_ui",
    "run_setup_with_terminal_status",
    "build_platform_services",
    "build_artifact_services_for_provider",
    "build_lxc_artifact_services",
    "build_deployment_services_for_provider",
    "build_lxc_deployment_services",
    "build_setup_services",
    "build_classic_update_workflow",
    "build_application_services",
)

_BOUNDARY_MODULES = {
    "build_host_preparation_service": "composition_platform",
    "build_platform_services": "composition_platform",
    "build_artifact_services_for_provider": "composition_artifacts",
    "build_lxc_artifact_services": "composition_artifacts",
    "build_deployment_services_for_provider": "composition_deployment",
    "build_lxc_deployment_services": "composition_deployment",
    "build_setup_services": "composition_setup",
    "build_classic_update_workflow": "composition_setup",
    "build_application_services": "composition_setup",
    "run_setup_with_terminal_status": "composition_setup",
}


def _delegate(name: str, *args: Any, **kwargs: Any) -> Any:
    _sync_compatibility_overrides()
    module_name = _BOUNDARY_MODULES.get(name)
    if module_name is None:
        return getattr(_runtime, name)(*args, **kwargs)
    module = importlib.import_module(f".{module_name}", __package__)
    return getattr(module, name)(*args, **kwargs)


def _sync_compatibility_overrides() -> None:
    """Make legacy facade patch points visible to the internal runtime module.

    Existing tests and integrations patch selected composition symbols. The
    facade remains the supported patch/import surface, so an explicitly
    replaced facade attribute is copied to the runtime module immediately
    before a delegated builder runs. Unmodified builder wrappers restore the
    original runtime callable and never create a recursive alias.
    """

    _sync_runtime_overrides()
    _refresh_loaded_boundary_modules()


def _sync_runtime_overrides() -> None:
    for name, original in _RUNTIME_ORIGINALS.items():
        facade_value = globals().get(name, original)
        if facade_value is _FACADE_DEFAULTS[name]:
            setattr(_runtime, name, original)
        else:
            setattr(_runtime, name, facade_value)

    for name, original in _RUNTIME_DEFAULTS.items():
        if name in _RUNTIME_BUILDER_NAMES:
            continue
        setattr(_runtime, name, globals().get(name, original))


def _refresh_loaded_boundary_modules() -> None:
    for module_name in set(_BOUNDARY_MODULES.values()):
        module = sys.modules.get(f"{__package__}.{module_name}")
        if module is None:
            continue
        refresh = getattr(module, "_refresh_runtime_symbols", None)
        if refresh is not None:
            refresh()
        _sync_boundary_overrides(module)


def _sync_boundary_overrides(module: Any) -> None:
    boundary_defaults = getattr(module, "_BOUNDARY_DEFAULTS", {})
    for name, default in boundary_defaults.items():
        facade_value = globals().get(name)
        if facade_value is _FACADE_DEFAULTS.get(name, default):
            setattr(module, name, default)
        else:
            setattr(module, name, facade_value)


def __getattr__(name: str) -> Any:
    """Expose established runtime symbols without copying implementation here."""

    value = getattr(_runtime, name)
    if isinstance(value, FunctionType):
        def delegated(*args: Any, **kwargs: Any) -> Any:
            return _delegate(name, *args, **kwargs)

        delegated.__name__ = value.__name__
        delegated.__doc__ = value.__doc__
        return delegated
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_runtime)))


def build_application_logger(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_application_logger", *args, **kwargs)


def build_host_environment_detector(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_host_environment_detector", *args, **kwargs)


def build_host_detection_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_host_detection_service", *args, **kwargs)


def build_host_preparation_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_host_preparation_service", *args, **kwargs)


def build_project_filesystem_inspector(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_project_filesystem_inspector", *args, **kwargs)


def build_preflight_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_preflight_service", *args, **kwargs)


def build_configuration_validation_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_configuration_validation_service", *args, **kwargs)


def build_compose_file_repository(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_compose_file_repository", *args, **kwargs)


def build_network_doctor_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_network_doctor_service", *args, **kwargs)


def build_read_only_hang_diagnostics(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_read_only_hang_diagnostics", *args, **kwargs)


def build_preflight_evidence_writer(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_preflight_evidence_writer", *args, **kwargs)


def build_process_runner(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_process_runner", *args, **kwargs)


def build_network_repair_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_network_repair_service", *args, **kwargs)


def build_network_repair_options(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_network_repair_options", *args, **kwargs)


def build_post_install_preflight_service(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_post_install_preflight_service", *args, **kwargs)


def build_setup_ui(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_setup_ui", *args, **kwargs)


async def run_setup_with_terminal_status(*args: Any, **kwargs: Any) -> Any:
    return await _delegate("run_setup_with_terminal_status", *args, **kwargs)


def build_platform_services(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_platform_services", *args, **kwargs)


def build_artifact_services_for_provider(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_artifact_services_for_provider", *args, **kwargs)


def build_lxc_artifact_services(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_lxc_artifact_services", *args, **kwargs)


def build_deployment_services_for_provider(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_deployment_services_for_provider", *args, **kwargs)


def build_lxc_deployment_services(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_lxc_deployment_services", *args, **kwargs)


def build_setup_services(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_setup_services", *args, **kwargs)


def build_classic_update_workflow(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_classic_update_workflow", *args, **kwargs)


def build_application_services(*args: Any, **kwargs: Any) -> Any:
    return _delegate("build_application_services", *args, **kwargs)


_FACADE_DEFAULTS = {
    name: globals()[name]
    for name in _RUNTIME_BUILDER_NAMES
}
_RUNTIME_ORIGINALS = {
    name: getattr(_runtime, name)
    for name in _RUNTIME_BUILDER_NAMES
}
_RUNTIME_PATCHABLE_NAMES = frozenset(dir(_runtime))
_RUNTIME_DEFAULTS = {
    name: getattr(_runtime, name)
    for name in _RUNTIME_PATCHABLE_NAMES
}
__all__ = [name for name in dir(_runtime) if not name.startswith("_")] + list(
    _RUNTIME_BUILDER_NAMES
)
