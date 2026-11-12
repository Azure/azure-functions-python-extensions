#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic dynamic payload tests for the Dataverse/CDS connector bindings."""

import copy
import json
import unittest
from types import SimpleNamespace
from typing import List

import azure.connectors.commondataservice as models
import azurefunctions.extensions.connectors.commondataservice as cds
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.connectorConverter import ConnectorConverter


class TestCommonDataServiceBindings(unittest.TestCase):
    """Retain dynamic webhook data separately from legacy polling batches."""

    def test_public_bindings_reuse_sdk_models(self):
        """Use SDK Item and ObjectEntity without a fake fixed row schema."""
        self.assertIn("ConnectorConverter", cds.__all__)
        for name, model_type in (
            ("Item", models.Item),
            ("RowChangeNotification", models.ObjectEntity),
            ("ActionEventNotification", models.ObjectEntity),
        ):
            binding_type = getattr(cds, name)
            with self.subTest(name=name):
                self.assertIn(name, cds.__all__)
                self.assertTrue(issubclass(binding_type, model_type))
                self.assertFalse(binding_type.supports_deferred_binding())
                for annotation in (
                    binding_type, List[binding_type], list[binding_type],
                ):
                    self.assertTrue(
                        ConnectorConverter.check_input_type_annotation(annotation),
                    )
                    self.assertIsNone(ConnectorConverter.decode(
                        data=None, trigger_metadata=None, pytype=annotation,
                    ))
        self.assertFalse(ConnectorConverter.check_input_type_annotation(models.Item))
        self.assertFalse(ConnectorConverter.check_input_type_annotation(
            models.ObjectEntity,
        ))

    def test_legacy_item_preserves_raw_column_types_and_odata_keys(self):
        """Keep all column values without request-serializer filtering."""
        record = {
            "accountid": "row-1", "name": "Example \u00e9quipe",
            "enabled": False, "count": 0, "optional": None, "empty": "",
            "tags": ["one", None], "owner": {"id": "owner-1", "custom": False},
            "_ownerid_value": "owner-1",
            "_ownerid_value@OData.Community.Display.V1.FormattedValue": "Owner",
            "@odata.etag": 'W/"123"',
        }
        original = copy.deepcopy(record)
        for payload in (
            record, {"body": record}, [record], {"body": [record]},
            {"value": [record]},
            {"body": {"@odata.context": "rows", "value": [record]}},
        ):
            text = json.dumps(payload, ensure_ascii=False)
            for value in (
                payload, text, text.encode("utf-8"), bytearray(text.encode()),
            ):
                with self.subTest(value=value):
                    result = ConnectorConverter.decode(
                        data=Datum(value=value, type="json"),
                        trigger_metadata=None, pytype=List[cds.Item],
                    )
                    self.assertIsInstance(result, list)
                    self.assertEqual(len(result), 1)
                    self.assertIs(type(result[0]), models.Item)
                    self.assertEqual(result[0].dynamic_properties, record)
        self.assertEqual(record, original)

    def test_legacy_item_accepts_only_a_sole_explicit_property_bag(self):
        """Do not merge a real dynamicProperties column into other columns."""
        for key in ("dynamicProperties", "dynamic_properties"):
            for bag in ({"accountid": "row-1", "optional": None}, {}, None):
                with self.subTest(key=key, bag=bag):
                    result = cds.Item(data=Datum(value={key: bag}, type="json"))
                    self.assertEqual(result.get_sdk_type()[0].dynamic_properties, bag)
            record = {"accountid": "row-1", key: {"nested": True}}
            self.assertEqual(cds.Item(data=Datum(
                value=record, type="json",
            )).get_sdk_type()[0].dynamic_properties, record)

    def test_webhooks_preserve_entire_row_or_action_callback(self):
        """No schema, property-bag, or event-field names receive special treatment."""
        record = {
            "accountid": "row-1", "SdkMessage": "Update",
            "entityOutputs": {"name": "Example", "optional": None},
            "InputParameters": [{"key": "amount", "value": 0}],
            "OutputParameters": {"succeeded": False},
            "value": [{"id": "nested"}], "body": {"custom": "column"},
            "schema": {"custom": True}, "dynamicProperties": {"column": None},
            "additional_properties": {"column": False},
            "@odata.id": "row-odata-id", "count": 0, "optional": None,
        }
        original = copy.deepcopy(record)
        for binding_type in (cds.RowChangeNotification, cds.ActionEventNotification):
            for payload in (record, {"body": record}, [record], {"body": [record]}):
                text = json.dumps(payload)
                for value in (payload, text, text.encode("utf-8")):
                    with self.subTest(binding=binding_type, value=value):
                        result = ConnectorConverter.decode(
                            data=Datum(value=value, type="json"),
                            trigger_metadata=None, pytype=List[binding_type],
                        )
                        self.assertEqual(len(result), 1)
                        self.assertIs(type(result[0]), models.ObjectEntity)
                        self.assertEqual(result[0].additional_properties, record)
                        self.assertNotIsInstance(
                            result[0], models.WebhookNotificationContent,
                        )
        self.assertEqual(record, original)

    def test_webhook_value_only_records_do_not_disappear_or_split(self):
        """A webhook value field is data, even when it contains an empty array."""
        for binding_type in (cds.RowChangeNotification, cds.ActionEventNotification):
            for value in ([], None, [{"id": "first"}, {"id": "second"}], "text"):
                with self.subTest(binding=binding_type, value=value):
                    result = binding_type(data=Datum(
                        value={"body": {"value": value}}, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].additional_properties, {"value": value})

    def test_webhook_schema_and_property_bag_keys_remain_payload_fields(self):
        """Do not treat a table or action field as schema-discovery metadata."""
        for binding_type in (cds.RowChangeNotification, cds.ActionEventNotification):
            for record in ({"schema": None}, {"dynamicProperties": {"name": "Example"}},
                           {"additional_properties": {"optional": None}}):
                with self.subTest(binding=binding_type, record=record):
                    result = binding_type(data=Datum(
                        value=record, type="json",
                    )).get_sdk_type()
                    self.assertEqual(result[0].additional_properties, record)

    def test_value_and_body_columns_are_preserved_on_legacy_records(self):
        """Only value plus OData metadata identifies a polling envelope."""
        for value in ([], None, [{"accountid": "nested"}], "custom", False):
            record = {"accountid": "row-1", "value": value, "body": {"text": "custom"}}
            for payload in (record, {"body": record}, {"value": [record]}):
                with self.subTest(payload=payload):
                    result = cds.Item(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0].dynamic_properties, record)

    def test_empty_callbacks_and_records_have_distinct_meanings(self):
        """Keep empty records distinct from no-work arrays or null bodies."""
        for binding_type in (
            cds.Item, cds.RowChangeNotification, cds.ActionEventNotification,
        ):
            for payload in ([], {"body": None}, {"body": []}):
                with self.subTest(binding=binding_type, payload=payload):
                    self.assertEqual(binding_type(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type(), [])
            record = binding_type(data=Datum(value={}, type="json")).get_sdk_type()
            self.assertEqual(len(record), 1)
            self.assertEqual(
                record[0].dynamic_properties if binding_type is cds.Item
                else record[0].additional_properties, {},
            )
        for value in ([], None):
            self.assertEqual(cds.Item(data=Datum(
                value={"value": value}, type="json",
            )).get_sdk_type(), [])

    def test_transport_collections_preserve_order_and_webhook_boundaries(self):
        """Normalize polling batches but preserve webhook value collections."""
        cases = (
            (cds.Item, [{"body": {"accountid": "row-1"}},
                        {"value": [{"accountid": "row-2"}]}],
             [{"accountid": "row-1"}, {"accountid": "row-2"}]),
            (cds.RowChangeNotification,
             [{"body": {"value": []}}, {"value": [{"id": "nested"}]}],
             [{"value": []}, {"value": [{"id": "nested"}]}]),
            (cds.ActionEventNotification,
             [[{"name": "first"}], {"body": {"name": "second"}}],
             [{"name": "first"}, {"name": "second"}]),
        )
        for binding_type, events, expected in cases:
            text = [json.dumps(event) for event in events]
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=text)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[value.encode() for value in text],
                )),
            ):
                with self.subTest(binding=binding_type, data_type=data_type):
                    result = binding_type(data=Datum(value=collection, type=data_type))
                    self.assertEqual([
                        item.dynamic_properties if binding_type is cds.Item
                        else item.additional_properties
                        for item in result.get_sdk_type()
                    ], expected)

    def test_empty_transport_collections(self):
        """No transport events produce no SDK records."""
        for binding_type in (
            cds.Item, cds.RowChangeNotification, cds.ActionEventNotification,
        ):
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=[])),
                ("collection_bytes", SimpleNamespace(bytes=[])),
            ):
                self.assertEqual(binding_type(data=Datum(
                    value=collection, type=data_type,
                )).get_sdk_type(), [])

    def test_invalid_payloads_raise_for_all_bindings(self):
        """Do not silently drop malformed records, envelopes, or JSON bytes."""
        for binding_type in (
            cds.Item, cds.RowChangeNotification, cds.ActionEventNotification,
        ):
            for payload in ("invalid", b"\xff", None, 1, {"body": "bad"},
                            [{"accountid": "valid"}, None], [False]):
                with self.subTest(binding=binding_type, payload=payload):
                    with self.assertRaises(ValueError):
                        binding_type(data=Datum(
                            value=payload, type="json",
                        )).get_sdk_type()
            with self.assertRaisesRegex(ValueError, "No data provided"):
                binding_type(data=None).get_sdk_type()

    def test_invalid_legacy_batches_and_property_bags_raise(self):
        """Validate collection and property-bag shapes without dropping values."""
        for payload in ({"value": "bad"}, {"value": [{"id": "valid"}, None]},
                        {"dynamicProperties": []}, {"dynamic_properties": False}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    cds.Item(data=Datum(value=payload, type="json")).get_sdk_type()

    def test_sdk_registry_confirms_the_three_legacy_payload_envelopes(self):
        """Webhook conversion must not depend on the incomplete SDK trigger registry."""
        registry = getattr(models, "TRIGGER_OPERATIONS", None)
        if registry is None:
            self.skipTest("This SDK does not expose a CDS trigger registry.")
        for operation in (
            "GetOnDeletedItems_V2", "GetOnNewItems_V2", "GetOnUpdatedItems_V2",
        ):
            with self.subTest(operation=operation):
                self.assertEqual(
                    registry[operation]["callback_payload_type"], "ItemsList",
                )
