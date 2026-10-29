#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Regression tests for generated model-or-mapping annotations."""

import unittest
from dataclasses import dataclass
from typing import Any, Mapping

from azurefunctions.extensions.connectors._deserialization import deserialize_model


@dataclass
class NestedModel:
    """Represent a generated nested SDK model."""

    id: str | None = None


@dataclass
class ContainerModel:
    """Mirror the SDK's nullable model-or-mapping and collection fields."""

    child: NestedModel | Mapping[str, Any] | None = None
    children: list[NestedModel | Mapping[str, Any]] | None = None
    properties: Mapping[str, Any] | None = None
    ambiguous: NestedModel | str | None = None


class TestSdkModelDeserialization(unittest.TestCase):
    """Keep generated mapping fallbacks from disabling typed receive models."""

    def test_model_mapping_union_deserializes_nested_model(self):
        """Prefer the unique model when the other branch accepts mappings."""
        result = deserialize_model(ContainerModel, {"child": {"id": "child-1"}})
        self.assertIsInstance(result.child, NestedModel)
        self.assertEqual(result.child.id, "child-1")

    def test_model_mapping_union_deserializes_collection_items(self):
        """Apply the same rule inside generated list annotations."""
        result = deserialize_model(ContainerModel, {"children": [
            {"id": "child-1"}, {"id": "child-2"},
        ]})
        self.assertEqual(len(result.children), 2)
        self.assertTrue(all(
            isinstance(child, NestedModel) for child in result.children
        ))
        self.assertEqual(
            [child.id for child in result.children], ["child-1", "child-2"],
        )

    def test_null_union_and_untyped_mapping_are_preserved(self):
        """Do not convert arbitrary JSON objects into guessed model types."""
        properties = {"Optional": None, "Count": 0, "Nested": {"Enabled": False}}
        result = deserialize_model(ContainerModel, {
            "child": None, "properties": properties,
        })
        self.assertIsNone(result.child)
        self.assertEqual(result.properties, properties)

    def test_non_mapping_union_is_not_guessed(self):
        """Leave unrelated unions on the existing passthrough path."""
        for value in ("text", {"id": "unresolved"}):
            with self.subTest(value=value):
                result = deserialize_model(ContainerModel, {"ambiguous": value})
                self.assertEqual(result.ambiguous, value)
