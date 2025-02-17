import unittest

from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder


class TestFluentYAMLBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = FluentYAMLBuilder("root")

    def test_initialization(self):
        """Test that the builder initializes with the correct root name."""
        self.assertEqual(self.builder.root.name, "root")
        self.assertIsNone(self.builder.root.value)
        self.assertEqual(len(self.builder.root.children), 0)

    def test_add_child(self):
        """Test that a child node is correctly added."""
        self.builder.add_child("child1", "value1")
        self.assertEqual(len(self.builder.root.children), 1)
        self.assertEqual(self.builder.root.children[0].name, "child1")
        self.assertEqual(self.builder.root.children[0].value.to_dict(), "value1")

    def test_add_child_with_stay(self):
        """Test add_child with stay=True ensuring the current node remains unchanged."""
        self.builder.add_child("child1", "value1", stay=True)
        self.assertEqual(self.builder.current, self.builder.root)

    def test_up(self):
        """Test moving up the node hierarchy."""
        self.builder.add_child("child1", "value1")
        self.builder.up()
        self.assertEqual(self.builder.current, self.builder.root)

    def test_to_dict_single_node(self):
        """Test to_dict method with a single node."""
        result = self.builder.to_dict()
        self.assertEqual(result, {"root": {}})

    def test_to_dict_with_children(self):
        """Test to_dict with multiple children."""
        (self.builder
         .add_child("child1")
         .add_child("child2", "value2")
         .up().up()
         .add_child("child3", "value3"))
        result = self.builder.to_dict()
        expected = {
            "root": {
                "child1": {
                    "child2": "value2"
                },
                "child3": "value3"
            }
        }
        self.assertEqual(expected, result)

    def test_to_dict_with_multiple_children(self):
        self.builder.add_child("child1", "value1", stay=True).add_child("child2", "value2")
        result = self.builder.to_dict(self.builder.root)
        self.assertEqual({"root": {"child1": "value1", "child2": "value2"}}, result)

    def test_to_dict_with_duplicate_children(self):
        self.builder.add_child(name="child", value="value1", stay=True)
        self.builder.add_child(name="child", value="value2")

        result = self.builder.to_dict()
        self.assertEqual(result, {"root": {"child": ["value1", "value2"]}})

    def test_build(self):
        self.builder.add_child("key", value="value")
        result = self.builder.build()
        expected = {"root": {"key": "value"}}
        self.assertEqual(expected, result)

    def test_to_yaml(self):
        """Test generating YAML output."""
        self.builder.add_child("child1").add_child("child2", "value2")
        self.builder.up().up()
        self.builder.add_child("child3", "value3")
        yaml_output = self.builder.to_yaml()
        expected_yaml = (
            "root:\n"
            "  child1:\n"
            "    child2: value2\n"
            "  child3: value3\n"
        )
        self.assertEqual(expected_yaml.strip(), yaml_output.strip())


if __name__ == "__main__":
    unittest.main()
