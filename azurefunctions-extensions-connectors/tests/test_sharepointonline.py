#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Tests for SharePoint Online trigger SDK bindings."""

import copy
import json
import unittest
from types import SimpleNamespace
from typing import List

import azure.connectors.sharepointonline as models
import azurefunctions.extensions.connectors.sharepointonline as sharepointonline
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.sharepointonline import (
    ConnectorConverter,
    DeletedItem,
    Item,
)


class TestSharePointOnlineBindings(unittest.TestCase):
    """Preserve dynamic columns and deserialize deletion metadata."""

    def test_public_bindings_use_generated_sdk_models(self):
        """Expose item fields while reusing the common converter."""
        for binding_type, model_type in (
            (Item, models.Item), (DeletedItem, models.DeletedItem),
        ):
            with self.subTest(binding=binding_type):
                self.assertIn(binding_type.__name__, sharepointonline.__all__)
                self.assertTrue(issubclass(binding_type, model_type))
                self.assertFalse(binding_type.supports_deferred_binding())

    def test_converter_accepts_direct_and_list_bindings(self):
        """Recognize both SharePoint bindings without a type registry."""
        for annotation in (
            Item, List[Item], list[Item],
            DeletedItem, List[DeletedItem], list[DeletedItem],
        ):
            with self.subTest(annotation=annotation):
                self.assertTrue(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )
                self.assertIsNone(ConnectorConverter.decode(
                    data=None, trigger_metadata=None, pytype=annotation,
                ))

    def test_generated_models_are_not_binding_annotations(self):
        """Require extension wrappers instead of plain generated models."""
        for annotation in (models.Item, models.DeletedItem, List[models.Item]):
            with self.subTest(annotation=annotation):
                self.assertFalse(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )

    def test_item_preserves_flat_dynamic_columns_and_nested_values(self):
        """Retain raw JSON values without request-serialization conversions."""
        record = {
            "ID": 42,
            "Title": "Planning \u00e9quipe",
            "CustomFlag": False,
            "CustomCount": 0,
            "CustomText": "",
            "CustomValue": None,
            "Author": {"DisplayName": "Example", "Email": None},
            "Tags": ["one", "two"],
            "Children": [{"ID": 1}, None, False],
            "{FilenameWithExtension}": "plan.docx",
            "@odata.etag": '"1"',
        }
        original = copy.deepcopy(record)
        for payload in (
            record,
            {"body": record},
            {"value": [record]},
            {"body": {"@odata.context": "items", "value": [record]}},
            [record],
            {"body": [record]},
        ):
            for value in (
                payload, json.dumps(payload), json.dumps(payload).encode("utf-8"),
            ):
                with self.subTest(value=value):
                    result = ConnectorConverter.decode(
                        data=Datum(value=value, type="json"),
                        trigger_metadata=None,
                        pytype=List[Item],
                    )
                    self.assertIsInstance(result, list)
                    self.assertEqual(len(result), 1)
                    self.assertIsInstance(result[0], models.Item)
                    self.assertEqual(result[0].dynamic_properties, original)
        self.assertEqual(record, original)

    def test_item_supports_explicit_sdk_property_bag(self):
        """Read the SDK's sole dynamicProperties object without nesting it."""
        properties = {"ID": 42, "Title": "Example", "OptionalColumn": None}
        for property_name in ("dynamicProperties", "dynamic_properties"):
            for value in (properties, {}, None):
                with self.subTest(property_name=property_name, value=value):
                    result = Item(data=Datum(value={
                        "body": {property_name: value},
                    }, type="json")).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].dynamic_properties, value)

    def test_item_does_not_flatten_property_bag_named_columns(self):
        """Keep all columns when a record also has a dynamicProperties key."""
        record = {"ID": 42, "dynamicProperties": {"Title": "Nested column"}}
        result = Item(data=Datum(value={"body": record}, type="json")).get_sdk_type()
        self.assertEqual(result[0].dynamic_properties, record)

    def test_value_and_body_columns_are_not_envelopes(self):
        """Do not drop records whose custom columns use envelope-like names."""
        for value_column in ([{"ID": 100}], [], None, "custom", 0, False):
            record = {
                "ID": 42,
                "value": value_column,
                "body": {"Text": "Custom body column"},
            }
            for payload in (record, {"body": record}, {"value": [record]}):
                with self.subTest(payload=payload):
                    result = Item(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].dynamic_properties, record)

    def test_deleted_item_reads_all_wire_fields(self):
        """Honor ID and Pascal-case wire names, including false and zero."""
        record = {
            "ID": 0,
            "Name": "Planning",
            "FileNameWithExtension": "plan.docx",
            "DeletedByUserName": "Example User",
            "TimeDeleted": "2026-10-21T10:00:00Z",
            "IsFolder": False,
        }
        for payload in (record, {"body": record}, {"value": [record]}, [record]):
            for value in (payload, json.dumps(payload)):
                with self.subTest(value=value):
                    result = ConnectorConverter.decode(
                        data=Datum(value=value, type="json"),
                        trigger_metadata=None,
                        pytype=List[DeletedItem],
                    )
                    self.assertEqual(len(result), 1)
                    self.assertIsInstance(result[0], models.DeletedItem)
                    self.assertEqual(result[0].id, 0)
                    self.assertEqual(result[0].name, "Planning")
                    self.assertEqual(result[0].file_name_with_extension, "plan.docx")
                    self.assertEqual(result[0].deleted_by_user_name, "Example User")
                    self.assertEqual(result[0].time_deleted, record["TimeDeleted"])
                    self.assertIs(result[0].is_folder, False)

    def test_deleted_item_accepts_python_field_names(self):
        """Keep the shared deserializer's Python-field fallback."""
        result = DeletedItem(data=Datum(value={
            "id": 1, "name": "Folder", "is_folder": True,
        }, type="json")).get_sdk_type()
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[0].name, "Folder")
        self.assertIs(result[0].is_folder, True)
        self.assertIsNone(result[0].time_deleted)

    def test_empty_batches_and_null_callback_bodies(self):
        """Represent no-work callbacks as empty lists for both bindings."""
        for binding_type in (Item, DeletedItem):
            for payload in (
                [], {"body": None}, {"body": []}, {"value": []},
                {"body": {"value": None}},
                {"@odata.context": "items", "value": []},
            ):
                with self.subTest(binding=binding_type, payload=payload):
                    self.assertEqual(binding_type(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type(), [])

    def test_poll_many_collections_preserve_both_payload_families(self):
        """Flatten transport events and source batches in order."""
        records = [{"ID": 1, "Name": "First"}, {"ID": 2, "Name": "Second"}]
        events = [
            json.dumps({"body": records[0]}),
            json.dumps({"body": {"value": records[1:]}}),
        ]
        for binding_type in (Item, DeletedItem):
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=events)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[event.encode("utf-8") for event in events],
                )),
            ):
                with self.subTest(binding=binding_type, data_type=data_type):
                    result = ConnectorConverter.decode(
                        data=Datum(value=collection, type=data_type),
                        trigger_metadata=None,
                        pytype=binding_type,
                    )
                    if binding_type is Item:
                        self.assertEqual(
                            [item.dynamic_properties for item in result], records,
                        )
                    else:
                        self.assertEqual(
                            [(item.id, item.name) for item in result],
                            [(1, "First"), (2, "Second")],
                        )

    def test_empty_poll_many_collections(self):
        """An empty transport collection contains no records."""
        for binding_type in (Item, DeletedItem):
            with self.subTest(binding=binding_type):
                self.assertEqual(binding_type(data=Datum(
                    value=SimpleNamespace(string=[]), type="collection_string",
                )).get_sdk_type(), [])

    def test_invalid_payloads_raise_instead_of_dropping_records(self):
        """Reject malformed JSON, envelopes, and batch members."""
        for binding_type in (Item, DeletedItem):
            for value in (
                "not-json", 42, None, {"body": "not-an-object"},
                {"value": "not-an-array"}, {"value": [{"ID": 1}, None]},
                {"body": {"value": [False]}}, [{"ID": 1}, 2],
            ):
                with self.subTest(binding=binding_type, value=value):
                    with self.assertRaises(ValueError):
                        ConnectorConverter.decode(
                            data=Datum(value=value, type="json"),
                            trigger_metadata=None,
                            pytype=binding_type,
                        )

    def test_missing_data_raises_for_both_wrappers(self):
        """Direct wrapper construction still reports missing input."""
        for binding_type in (Item, DeletedItem):
            with self.subTest(binding=binding_type):
                with self.assertRaisesRegex(ValueError, "No data provided"):
                    binding_type(data=None).get_sdk_type()

    def test_invalid_explicit_property_bag_raises(self):
        """Do not hide invalid SDK property bags as empty items."""
        for value in ([], "invalid", 1, False):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "dynamicProperties"):
                    Item(data=Datum(value={
                        "dynamicProperties": value,
                    }, type="json")).get_sdk_type()

    def test_all_model_backed_trigger_operations_have_item_bindings(self):
        """Cover eight item operations and both deletion operations."""
        operation_groups = (
            (
                ("GetOnNewItems", "GetOnUpdatedItems", "GetOnChangedItems",
                 "GetOnNewFileItems", "GetOnUpdatedFileItems",
                 "GetOnUpdatedFileClassifiedTimes", "GetOnNewItemsFromForm",
                 "GetOnRecurrenceDigest"),
                "ItemsList", Item,
            ),
            (
                ("GetOnDeletedItems", "GetOnDeletedFileItems"),
                "DeletedItemList", DeletedItem,
            ),
        )
        for operations, envelope, binding_type in operation_groups:
            for operation in operations:
                with self.subTest(operation=operation):
                    self.assertEqual(
                        models.TRIGGER_OPERATIONS[operation]["callback_payload_type"],
                        envelope,
                    )
                    result = binding_type(data=Datum(value={"body": {"value": [{
                        "ID": 42, "Name": operation,
                    }]}}, type="json")).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    if binding_type is Item:
                        self.assertIsInstance(result[0], models.Item)
                        self.assertEqual(
                            result[0].dynamic_properties["Name"], operation,
                        )
                    else:
                        self.assertIsInstance(result[0], models.DeletedItem)
                        self.assertEqual(result[0].name, operation)
