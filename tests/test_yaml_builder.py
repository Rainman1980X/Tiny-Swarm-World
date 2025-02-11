import unittest

from docker.adapters.yaml.yaml_builder import FluentYAMLBuilder


class TestFluentYAMLBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = FluentYAMLBuilder()

    def test_init_default_structure(self):
        self.assertEqual(self.builder.build(), {})

    def test_add_key(self):
        self.builder.add_key("key")
        self.assertEqual(self.builder.build(), {"key": {}})

    def test_add_nested_key(self):
        self.builder.add_key("parent").add_key("child")
        self.assertEqual(self.builder.build(), {"parent": {"child": {}}})

    def test_add_list(self):
        self.builder.add_list("items")
        self.assertEqual(self.builder.build(), {"items": []})

    def test_add_list_item(self):
        self.builder.add_list("items").add_list_item("item1")
        self.assertEqual(self.builder.build(), {"items": ["item1"]})

    def test_add_entry(self):
        self.builder.add_entry("key", "value")
        self.assertEqual(self.builder.build(), {"key": "value"})

    def test_add_list_with_entries(self):
        self.builder.add_list("items").add_list_item({"key1": "value1"}).add_list_item({"key2": "value2"})
        self.assertEqual(self.builder.build(), {"items": [{"key1": "value1"}, {"key2": "value2"}]})

    def test_up_navigation(self):
        self.builder.add_key("parent").add_key("child").up()
        self.builder.add_entry("sibling", "value")
        self.assertEqual(self.builder.build(), {"parent": {"child": {}, "sibling": "value"}})

    def test_to_yaml(self):
        self.builder.add_key("key").add_entry("subkey", "value")
        yaml_output = self.builder.to_yaml()
        self.assertIn("key:\n  subkey: value", yaml_output)

    def test_raise_error_when_adding_key_on_non_dict(self):
        self.builder.add_list("items")
        with self.assertRaises(ValueError):
            self.builder.add_key("key_in_list")

    def test_raise_error_when_adding_list_on_non_dict(self):
        self.builder.add_list("items")
        with self.assertRaises(ValueError):
            self.builder.add_list("list_in_list")

    def test_raise_error_when_adding_entry_on_non_dict(self):
        self.builder.add_list("items")
        with self.assertRaises(ValueError):
            self.builder.add_entry("key", "value")

    def test_raise_error_when_adding_item_to_non_list(self):
        self.builder.add_key("key")
        with self.assertRaises(ValueError):
            self.builder.add_list_item("item")


if __name__ == "__main__":
    unittest.main()
