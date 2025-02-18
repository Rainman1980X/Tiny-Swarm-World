import unittest

from docker.adapters.yaml.yaml_builder import YAMLNode, Value


class TestYAMLNode(unittest.TestCase):
    def setUp(self):
        self.root = YAMLNode("root")

    def test_add_child(self):
        self.root.add_child("child", "value1")
        self.assertEqual(len(self.root.children), 1)
        self.assertEqual(self.root.children[0].name, "child")
        self.assertEqual(self.root.children[0].value.to_dict(), "value1")

    def test_find_child(self):
        self.root.add_child("child1", "value1")
        self.root.add_child("child2", "value2")
        found_child = self.root.find_child("child2")
        self.assertIsNotNone(found_child)
        self.assertEqual(found_child.name, "child2")
        self.assertEqual(found_child.value.to_dict(), "value2")

    def test_remove_child(self):
        self.root.add_child("child1", "value1")
        self.root.add_child("child2", "value2")
        removed = self.root.remove_child("child1")
        self.assertTrue(removed)
        self.assertEqual(len(self.root.children), 1)
        self.assertEqual(self.root.children[0].name, "child2")

    def test_remove_child_not_found(self):
        self.root.add_child("child1", "value1")
        removed = self.root.remove_child("nonexistent")
        self.assertFalse(removed)
        self.assertEqual(len(self.root.children), 1)

    def test_find_child_not_found(self):
        self.root.add_child("child1", "value1")
        found_child = self.root.find_child("nonexistent")
        self.assertIsNone(found_child)

    def test_add_child_with_no_value(self):
        child = self.root.add_child("child")
        self.assertEqual(child.name, "child")
        self.assertIsNone(child.value)


class TestValue(unittest.TestCase):
    def test_value_initialization(self):
        value = Value("test_value")
        self.assertEqual(value.data, "test_value")

    def test_to_dict(self):
        value = Value({"key": "value"})
        self.assertEqual(value.to_dict(), {"key": "value"})


if __name__ == "__main__":
    unittest.main()
