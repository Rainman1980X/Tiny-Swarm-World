from ruamel.yaml import YAML


class FluentYAMLBuilder:
    """
    A Fluent API Builder for creating properly formatted YAML structures using ruamel.yaml.
    """

    def __init__(self):
        """Initialize the root YAML structure."""
        self._structure = {}
        self._current_level = self._structure
        self._history = []

    def add_key(self, key: str) -> 'FluentYAMLBuilder':
        """Adds a dictionary key at the current level."""
        if not isinstance(self._current_level, dict):
            raise ValueError("Current level is not a dictionary. Cannot add a key.")
        if key not in self._current_level:
            self._current_level[key] = {}
        self._history.append(self._current_level)
        self._current_level = self._current_level[key]
        return self

    def add_list(self, key: str) -> 'FluentYAMLBuilder':
        """Adds an empty list at the current level."""
        if not isinstance(self._current_level, dict):
            raise ValueError("Current level is not a dictionary. Cannot add a list.")
        self._current_level[key] = []
        self._history.append(self._current_level)
        self._current_level = self._current_level[key]
        return self

    def add_list_item(self, value: any) -> 'FluentYAMLBuilder':
        """Adds an item to the current list."""
        if not isinstance(self._current_level, list):
            raise ValueError("Current level is not a list. Cannot add an item.")
        self._current_level.append(value)
        return self

    def add_entry(self, key: str, value: any) -> 'FluentYAMLBuilder':
        """Adds a key-value pair to the current dictionary."""
        if not isinstance(self._current_level, dict):
            raise ValueError("Current level is not a dictionary. Cannot add an entry.")
        self._current_level[key] = value
        return self

    def up(self) -> 'FluentYAMLBuilder':
        """Moves up one level in the structure."""
        if self._history:
            self._current_level = self._history.pop()
        return self

    def build(self) -> dict:
        """Returns the final YAML structure."""
        return self._structure

    def to_yaml(self) -> str:
        """Converts the structure to YAML with correct indentation using ruamel.yaml."""
        yaml = YAML()
        yaml.default_flow_style = False  # Ensures correct list indentation
        yaml.indent(mapping=2, sequence=4, offset=2)  # Custom indentation settings

        from io import StringIO
        output = StringIO()
        yaml.dump(self._structure, output)
        return output.getvalue()


# Example Usage:
if __name__ == "__main__":
    builder = FluentYAMLBuilder()

    yaml_output = (
        builder
        .add_key("network")
        .add_key("ethernets")
        .add_key("ens3")
        .add_list("addresses")  # ✅ Erstellt eine leere Liste
        .add_list_item("10.34.157.239")  # ✅ Fügt Element zur Liste hinzu
        .up()
        .add_entry("gateway4", "10.34.157.1")
        .add_key("nameservers")
        .add_list("addresses")  # ✅ Erstellt eine leere Liste
        .add_list_item("8.8.8.8")  # ✅ Fügt Element zur Liste hinzu
        .add_list_item("8.8.4.4")  # ✅ Fügt weiteres Element zur Liste hinzu
        .up().up().up().up()
        .add_entry("renderer", "networkd")
        .add_entry("version", 2)
        .to_yaml()
    )

    print(yaml_output)
