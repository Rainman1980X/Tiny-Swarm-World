from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO


class Value:
    """Represents a generic data structure for YAML entries."""

    def __init__(self, value: Any):
        self.data = value  # Stores the direct value

    def to_dict(self):
        return self.data


class YAMLNode:
    """Represents a single node in a YAML tree structure."""

    def __init__(self, name: str, value: Any = None):
        self.name = name
        self.value = Value(value) if value is not None else None
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

class FluentYAMLBuilder:
    """Fluent API Builder for constructing properly formatted YAML structures using ruamel.yaml."""

    def __init__(self, root_name: str):
        self.root = YAMLNode(root_name)
        self.current = self.root

    def add_child(self, name: str, value: Any = None, stay: bool = False) -> "FluentYAMLBuilder":
        """Adds a child node and optionally remains at the current node."""
        new_child = self.current.add_child(name, value)
        if not stay:
            self.current = new_child
        return self

    def navigate_to(self, path: List[str]) -> "FluentYAMLBuilder":
        """Navigate to a specific entry by path."""
        node = self.root
        traversed_path = []  # Hält den erfolgreichen Navigationspfad

        for key in path:
            child = node.find_child(key)
            if child:  # Wenn ein Kind gefunden wurde, navigiere weiter
                node = child
                traversed_path.append(key)  # Füge den Schlüssel dem navigierten Pfad hinzu
            else:
                # Gebe detaillierte Fehlermeldung zu dem Punkt aus, an dem der Fehler auftritt
                raise KeyError(
                    f"Path not found at segment '{key}' after traversing: {'/'.join(traversed_path)}"
                )

        self.current = node  # Aktualisiere den aktuellen Knoten
        return self

    def navigate_to_recursively(self, name: str) -> "FluentYAMLBuilder":
        """Recursively find a node by its name, starting from the root."""

        def recursive_search(node, name_rc):
            if node.name == name_rc:
                return node
            for child in node.children:
                result_rc = recursive_search(child, name)
                if result_rc:
                    return result_rc
            return None

        result = recursive_search(self.root, name)
        if not result:
            raise KeyError(f"Node '{name}' not found in the tree.")
        self.current = result
        return self

    def delete_current(self) -> "FluentYAMLBuilder":
        """Deletes the current node and its subtree."""
        if self.current.parent:
            parent = self.current.parent
            parent.remove_child(self.current.name)
            self.current = parent
        else:
            raise ValueError("Cannot delete root node")
        return self

    def insert_at_current(self, name: str, value: Any = None) -> "FluentYAMLBuilder":
        """Inserts a new node at the current position."""
        self.current.add_child(name, value)
        return self

    def find_entry(self, name: str) -> Optional[Dict[str, Any]]:
        """Finds an entry by name and returns its dictionary representation."""
        for child in self.root.children:
            if child.name == name:
                return self.to_dict(child)
        return None

    def find_all_entries(self) -> List[Dict[str, Any]]:
        """Returns all entries as a list of dictionaries."""
        return [self.to_dict(child) for child in self.root.children]

    def up(self) -> "FluentYAMLBuilder":
        """Moves up one level in the tree if a parent exists."""
        if self.current.parent:
            self.current = self.current.parent
        return self

    def build(self):
        """Constructs the YAML dictionary, ensuring scalar values are stored correctly."""
        return self.to_dict()

    def to_dict(self, node: Optional[YAMLNode] = None) -> Dict[str, Any]:
        """Converts the tree structure into a correctly formatted dictionary for YAML export."""
        if node is None:
            node = self.root
        result = {}

        # If the node has a value, store it
        if node.value and node.value.to_dict() is not None:
            value = node.value.to_dict()
            return {node.name: value}  # Avoid unnecessary list conversion!

        for child in node.children:
            child_dict = self.to_dict(child)
            key, value = next(iter(child_dict.items()))

            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]  # Convert to a list if multiple entries exist
                result[key].append(value)
            else:
                result[key] = value  # No forced list conversion here!

        return {node.name: result} if result else {node.name: {}}

    def to_yaml(self) -> str:
        """Generates a YAML representation of the tree structure with proper formatting."""
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=4, offset=2)

        output = StringIO()
        yaml.dump(self.to_dict(), output)
        return output.getvalue()
