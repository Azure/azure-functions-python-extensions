#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic callback tests for Salesforce record trigger SDK bindings."""

import copy
import json
import unittest
from types import SimpleNamespace
from typing import List

import azure.connectors.salesforce as models
import azurefunctions.extensions.connectors.salesforce as salesforce
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.salesforce import ConnectorConverter, Item


class TestSalesforceBindings(unittest.TestCase):
    """Keep selected-object fields intact inside generated SDK item models."""

    def test_public_binding_uses_the_salesforce_sdk_item(self):
        """Expose SDK items without treating the envelope as the item model."""
        self.assertIn("Item", salesforce.__all__)
        self.assertIn("ConnectorConverter", salesforce.__all__)
        self.assertTrue(issubclass(Item, models.Item))
        self.assertFalse(Item.supports_deferred_binding())
        for annotation in (Item, List[Item], list[Item]):
            with self.subTest(annotation=annotation):
                self.assertTrue(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )
                result = ConnectorConverter.decode(
                    data=Datum(value={"Id": "record-1"}, type="json"),
                    trigger_metadata=None, pytype=annotation,
                )
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 1)
                self.assertIs(type(result[0]), models.Item)
                self.assertNotIsInstance(result[0], models.ItemsList)
                self.assertEqual(result[0].dynamic_properties, {"Id": "record-1"})
        self.assertFalse(ConnectorConverter.check_input_type_annotation(models.Item))

    def test_standard_and_custom_fields_keep_all_json_values(self):
        """Do not lose nulls, custom fields, relationships, or attributes."""
        record = {
            "Id": "record-1", "Name": "Example \u00e9quipe",
            "Active__c": False, "Count__c": 0, "Amount__c": 12.5,
            "Optional__c": None, "Empty__c": "", "Tags__c": ["one", None],
            "attributes": {"type": "Account", "url": "/sobjects/Account/record-1"},
            "Owner": {"Id": "owner-1", "Name": None},
            "Children__r": {"records": [{"Id": "child-1", "Optional__c": None}]},
        }
        original = copy.deepcopy(record)
        for payload in (
            record, [record], {"body": record}, {"body": [record]},
            {"value": [record]},
            {"body": {"value": [record], "@odata.nextLink": "next-page"}},
        ):
            text = json.dumps(payload, ensure_ascii=False)
            for value in (
                payload, text, text.encode("utf-8"), bytearray(text.encode()),
            ):
                with self.subTest(value=value):
                    result = Item(data=Datum(value=value, type="json")).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertIs(type(result[0]), models.Item)
                    self.assertEqual(result[0].dynamic_properties, original)
        self.assertEqual(record, original)

    def test_field_case_and_custom_names_are_not_normalized(self):
        """The property bag preserves wire identity even for similar keys."""
        record = {"Id": "upper", "id": "lower", "Custom__c": 1, "custom__c": 2,
                  "Account__r": {"Id": "relationship"}, "@odata.etag": "etag"}
        result = Item(data=Datum(value=record, type="json")).get_sdk_type()
        self.assertEqual(result[0].dynamic_properties, record)

    def test_sole_explicit_sdk_property_bag_is_supported(self):
        """Read the generated SDK bag without adding an extra nesting layer."""
        for key in ("dynamicProperties", "dynamic_properties"):
            for properties in ({"Id": "record-1", "Optional__c": None}, {}, None):
                with self.subTest(key=key, properties=properties):
                    result = Item(data=Datum(value={
                        "body": {key: properties},
                    }, type="json")).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].dynamic_properties, properties)

    def test_multi_key_records_do_not_merge_property_bag_named_fields(self):
        """Preserve root fields and a simultaneous explicit bag without collisions."""
        for key in ("dynamicProperties", "dynamic_properties"):
            record = {"Id": "root", key: {"Id": "nested", "Optional__c": None}}
            with self.subTest(key=key):
                result = Item(data=Datum(value=record, type="json")).get_sdk_type()
                self.assertEqual(result[0].dynamic_properties, record)

    def test_record_value_and_body_fields_do_not_hide_other_columns(self):
        """Only source envelopes, not selected-object records, get unwrapped."""
        for value in ([], None, [{"Id": "nested"}], "custom", False):
            record = {"Id": "record-1", "value": value, "body": {"Text": "custom"}}
            for payload in (record, {"body": record}, {"value": [record]}):
                with self.subTest(payload=payload):
                    result = Item(data=Datum(value=payload, type="json")).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].dynamic_properties, record)

    def test_poll_many_collections_keep_order_and_nested_record_fields(self):
        """Flatten transport events and source batches in delivery order."""
        records = [{"Id": "record-1"}, {"Id": "record-2", "Optional__c": None},
                   {"Id": "record-3", "Enabled__c": False}]
        events = [json.dumps({"body": records[0]}),
                  json.dumps({"value": records[1:]}), json.dumps([])]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=events)),
            ("collection_bytes", SimpleNamespace(
                bytes=[value.encode("utf-8") for value in events],
            )),
        ):
            with self.subTest(data_type=data_type):
                result = ConnectorConverter.decode(
                    data=Datum(value=collection, type=data_type),
                    trigger_metadata=None, pytype=List[Item],
                )
                self.assertEqual([item.dynamic_properties for item in result], records)

    def test_empty_batches_and_transport_collections(self):
        """No-work envelopes produce empty lists rather than empty SDK items."""
        for payload in ([], {"body": []}, {"body": None}, {"value": []},
                        {"@odata.context": "records", "value": None}):
            with self.subTest(payload=payload):
                self.assertEqual(Item(data=Datum(
                    value=payload, type="json",
                )).get_sdk_type(), [])
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=[])),
            ("collection_bytes", SimpleNamespace(bytes=[])),
        ):
            self.assertEqual(Item(data=Datum(
                value=collection, type=data_type,
            )).get_sdk_type(), [])
        empty_record = Item(data=Datum(value={}, type="json")).get_sdk_type()
        self.assertEqual(len(empty_record), 1)
        self.assertEqual(empty_record[0].dynamic_properties, {})

    def test_invalid_payloads_and_batch_members_raise(self):
        """Do not silently discard malformed records in an otherwise valid batch."""
        for payload in ("invalid", b"\xff", None, 1, {"body": "bad"},
                        {"value": "bad"}, {"value": [{"Id": "valid"}, None]},
                        [{"Id": "valid"}, False], {"body": [1]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    Item(data=Datum(value=payload, type="json")).get_sdk_type()

    def test_invalid_explicit_property_bags_raise(self):
        """Validate sole SDK property bags instead of losing their content."""
        for key in ("dynamicProperties", "dynamic_properties"):
            for value in ([], "bad", 1, False):
                with self.subTest(key=key, value=value):
                    with self.assertRaisesRegex(ValueError, "dynamicProperties"):
                        Item(data=Datum(value={key: value}, type="json")).get_sdk_type()

    def test_missing_data_follows_existing_converter_contract(self):
        """Converter no-data returns None; direct wrappers report missing input."""
        self.assertIsNone(ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=Item,
        ))
        with self.assertRaisesRegex(ValueError, "No data provided"):
            Item(data=None).get_sdk_type()

    def test_both_mapped_trigger_operations_use_items_list_envelopes(self):
        """Record creation and modification share this generated SDK item type."""
        registry = getattr(models, "TRIGGER_OPERATIONS", None)
        if registry is None:
            self.skipTest("This SDK does not expose a Salesforce trigger registry.")
        for operation in ("GetOnNewItems", "GetOnUpdatedItems"):
            with self.subTest(operation=operation):
                self.assertEqual(registry[operation]["method"], "get")
                self.assertEqual(registry[operation]["required_parameters"], ["table"])
                self.assertEqual(
                    registry[operation]["callback_payload_type"], "ItemsList",
                )
                result = Item(data=Datum(value={"body": {"value": [{
                    "Id": operation, "Custom__c": False,
                }]}}, type="json")).get_sdk_type()
                self.assertEqual(result[0].dynamic_properties,
                                 {"Id": operation, "Custom__c": False})
