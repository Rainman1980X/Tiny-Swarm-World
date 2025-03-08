from typing import Any


class YamlValue:
    """Represents a generic data structure for YAML entries."""

    def __init__(self, value: Any):
        self.data = value  # Stores the direct value

    def to_dict(self):
        return self.data