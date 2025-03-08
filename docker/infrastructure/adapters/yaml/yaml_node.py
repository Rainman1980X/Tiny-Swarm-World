from typing import Any, List, Optional

from infrastructure.adapters.yaml.yaml_value import YamlValue


class YAMLNode:
    """Represents a single node in a YAML tree structure."""

    def __init__(self, name: str, value: Any = None):
        self.name = name
        self.value = YamlValue(value) if value is not None else None
        self.parent: Optional["YAMLNode"] = None
        self.children: List["YAMLNode"] = []

    def add_child(self, name: str, value: Any = None) -> "YAMLNode":
        child = YAMLNode(name, value)
        child.parent = self
        self.children.append(child)
        return child

    def find_child(self, name: str) -> Optional["YAMLNode"]:
        """Find a child node by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None

    def remove_child(self, name: str) -> bool:
        """Remove a child node by name."""
        for i, child in enumerate(self.children):
            if child.name == name:
                del self.children[i]
                return True
        return False