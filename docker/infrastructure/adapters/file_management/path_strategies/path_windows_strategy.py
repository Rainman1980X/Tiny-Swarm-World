from pathlib import Path

from infrastructure.adapters.file_management.path_strategies.path_strategy import PathStrategy


class PathWindowsStrategy(PathStrategy):
    """Handles Windows-specific path normalization."""

    def normalize(self, path: Path) -> str:
        """Converts a Windows path to an absolute Unix-style path."""
        path = path.resolve()
        if path.drive:
            return "/" + "/".join(path.parts[1:])
        return path.as_posix()