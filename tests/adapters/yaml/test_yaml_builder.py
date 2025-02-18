import unittest

from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder, YAMLNode


class TestFluentYAMLBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = FluentYAMLBuilder("root")
        # self.root_node = self.builder.root
        # self.child_node = self.root_node.add_child("child", "value")
        # self.grandchild_node = self.child_node.add_child("grandchild", "value2")
        # self.builder.current = self.root_node

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

    def test_navigate_to_success(self):
        self.root_node = self.builder.root
        self.child_node = self.root_node.add_child("child", "value")
        self.grandchild_node = self.child_node.add_child("grandchild", "value2")
        self.builder.current = self.root_node
        path = ["child", "grandchild"]
        self.builder.navigate_to(path)
        self.assertEqual(self.builder.current, self.grandchild_node)

    def test_navigate_to_failure(self):
        path = ["nonexistent", "grandchild"]
        with self.assertRaises(KeyError) as context:
            self.builder.navigate_to(path)
        self.assertIn("Path not found", str(context.exception))

    def test_navigate_to_empty_path(self):
        self.root_node = self.builder.root
        self.child_node = self.root_node.add_child("child", "value")
        self.grandchild_node = self.child_node.add_child("grandchild", "value2")
        self.builder.current = self.root_node
        path = []
        self.builder.navigate_to(path)
        self.assertEqual(self.builder.current, self.root_node)  # Should stay at root

    def test_navigate_to_recursively_success(self):
        # Set up a simple structure
        self.builder.add_child("level1").add_child("level2")

        # Navigate to an existing node
        result = self.builder.navigate_to_recursively("level2")
        # Assert the current node has the expected name
        self.assertEqual(result.current.name, "level2")

    def test_navigate_to_recursively_node_not_found(self):
        # Set up a simple structure
        self.builder.add_child("level1").add_child("level2")

        # Attempt to navigate to a non-existing node
        with self.assertRaises(KeyError):
            self.builder.navigate_to_recursively("missing_node")

    def test_navigate_to_recursively_deep_node(self):
        # Set up a deeper nested structure
        self.builder.add_child("level1").add_child("level2").add_child("level3")

        # Navigate to a deep node
        result = self.builder.navigate_to_recursively("level3")
        # Assert the current node has the expected name
        self.assertEqual(result.current.name, "level3")

    def test_navigate_to_recursively_sibling_node(self):
        # Set up a structure with siblings
        self.builder.add_child("level1").add_child("child1").up().add_child("child2")

        # Navigate to a sibling node
        result = self.builder.navigate_to_recursively("child2")
        # Assert the current node has the expected name
        self.assertEqual(result.current.name, "child2")

    def test_delete_current_with_parent(self):
        # Set up a tree structure
        self.builder.add_child("child1")
        self.builder.add_child("child2")
        self.builder.navigate_to_recursively("child1")
        self.builder.add_child("subchild1")

        # Navigate to subchild1 and delete it
        self.builder.navigate_to_recursively("subchild1")
        result = self.builder.delete_current()

        # Verify subchild1 is removed
        parent = self.builder.find_entry("child1")
        self.assertIsNotNone(parent)
        self.assertIsNone(self.builder.find_entry("subchild1"))

        # Verify current node is updated to parent
        self.assertEqual(self.builder.current.name, "child1")
        self.assertIsInstance(result, FluentYAMLBuilder)

    def test_delete_current_without_parent_raises_error(self):
        with self.assertRaises(ValueError) as cm:
            self.builder.delete_current()

        self.assertEqual(str(cm.exception), "Cannot delete root node")

    def test_delete_current_updates_current_node(self):
        # Set up a tree structure
        self.builder.add_child("child1", stay=True)  # Add 'child1' under root
        self.builder.navigate_to(["child1"])  # Navigate to 'child1'
        self.builder.add_child("subchild1")  # Add 'subchild1' under 'child1'

        # Navigate to 'subchild1' and delete it
        self.builder.navigate_to(["child1", "subchild1"])  # Ensure correct path is followed
        self.builder.delete_current()  # Delete 'subchild1'

        # Verify that the current node is updated to 'child1' (the parent)
        current_node = self.builder.current
        self.assertEqual(current_node.name, "child1")  # Ensure current node is back to 'child1'

    def test_up(self):
        """Test moving up the node hierarchy."""
        self.builder.add_child("child1", "value1")
        self.builder.up()
        self.assertEqual(self.builder.current, self.builder.root)

    def test_up_with_parent(self):
        # Create a parent-child relationship
        parent_node = type("Node", (), {})()
        child_node = type("Node", (), {})()
        child_node.parent = parent_node
        self.builder.current = child_node

        # Call the 'up' method
        result = self.builder.up()

        # Assert that the current node is now set to its parent
        self.assertEqual(self.builder.current, parent_node)

        # Assert that the method returns the builder instance
        self.assertIs(result, self.builder)

    def test_up_without_parent(self):
        # Create a node with no parent
        node = type("Node", (), {})()
        node.parent = None
        self.builder.current = node

        # Call the 'up' method
        result = self.builder.up()

        # Assert that the current node remains unchanged
        self.assertIs(self.builder.current, node)

        # Assert that the method returns the builder instance
        self.assertIs(result, self.builder)

    def test_up_multiple_levels(self):
        # Create a multi-level hierarchy using YAMLNode
        grandparent_node = YAMLNode("grandparent")
        parent_node = grandparent_node.add_child("parent")
        child_node = parent_node.add_child("child")

        # Start the builder at the deepest node
        self.builder.current = child_node

        # Move up one level
        self.builder.up()
        self.assertEqual(self.builder.current, parent_node)

        # Move up another level
        self.builder.up()
        self.assertEqual(self.builder.current, grandparent_node)

        # Try moving up when no parent exists
        self.builder.up()  # Should simply return self without changes
        self.assertEqual(self.builder.current, grandparent_node)

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
