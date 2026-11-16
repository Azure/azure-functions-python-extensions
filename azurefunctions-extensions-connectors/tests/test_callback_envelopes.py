#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Keep callback transport metadata separate from connector record fields."""

import json
import unittest
from types import SimpleNamespace

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.commondataservice import Item as CdsItem
from azurefunctions.extensions.connectors.commondataservice import RowChangeNotification
from azurefunctions.extensions.connectors.dataflows import RefreshModel
from azurefunctions.extensions.connectors.office365 import GraphClientReceiveMessage
from azurefunctions.extensions.connectors.onedriveforbusiness import BlobMetadata
from azurefunctions.extensions.connectors.planner import GetTaskResponseV2
from azurefunctions.extensions.connectors.salesforce import Item as SalesforceItem
from azurefunctions.extensions.connectors.sharepointonline import Item as SharePointItem
from azurefunctions.extensions.connectors.teams import (
    ChatMessage, DynamicNewMessageWebhookTriggerResponseSchema,
)
from azurefunctions.extensions.connectors.visualstudioteamservices import BuildResult


class TestCallbackEnvelopes(unittest.TestCase):
    """Exercise envelope detection through the public SDK binding wrappers."""

    def _cases(self):
        """Supply one populated callback for each connector parser."""
        return (
            (BlobMetadata, {"Id": "file-1", "Name": "a.txt"}, "name", "a.txt", True),
            (GraphClientReceiveMessage, {"id": "mail-1", "subject": "Hello"},
             "subject", "Hello", True),
            (SharePointItem, {"ID": 7, "Title": "Hello"},
             "dynamic_properties", {"ID": 7, "Title": "Hello"}, True),
            (ChatMessage, {"id": "chat-1", "body": {"content": "Hello"}},
             "id", "chat-1", True),
            (CdsItem, {"id": "row-1"}, "dynamic_properties", {"id": "row-1"}, True),
            (SalesforceItem, {"Id": "record-1"},
             "dynamic_properties", {"Id": "record-1"}, True),
            (GetTaskResponseV2, {"id": "task-1"}, "id", "task-1", True),
            (BuildResult, {"id": 7}, "id", 7, True),
            (RefreshModel, {"dataflowId": "refresh-1"},
             "dataflow_id", "refresh-1", False),
        )

    def test_metadata_envelopes_populate_single_and_batch_fields(self):
        """Read body records and supported value batches despite metadata siblings."""
        for binding, record, field, expected, supports_batch in self._cases():
            bodies = (record, {"value": [record]}) if supports_batch else (record,)
            for body in bodies:
                for metadata in (
                    {"headers": {}}, {"headers": {"x-test": "value"}},
                    {"statusCode": 200}, {"headers": {}, "statusCode": 200},
                ):
                    envelope = {"body": body, **metadata}
                    for payload in (
                        envelope, json.dumps(envelope), json.dumps(envelope).encode(),
                    ):
                        with self.subTest(binding=binding, body=body, metadata=metadata,
                                          payload_type=type(payload)):
                            result = binding(data=Datum(
                                value=payload, type="json",
                            )).get_sdk_type()
                            self.assertEqual(len(result), 1)
                            self.assertEqual(getattr(result[0], field), expected)

    def test_poll_many_unwraps_each_event_in_order(self):
        """Apply envelope detection separately to each transport collection member."""
        for binding, record, field, expected, _ in self._cases():
            events = [json.dumps({"body": record, "headers": {}})] * 2
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=events)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[event.encode() for event in events],
                )),
            ):
                with self.subTest(binding=binding, data_type=data_type):
                    result = binding(data=Datum(
                        value=collection, type=data_type,
                    )).get_sdk_type()
                    self.assertEqual([getattr(item, field) for item in result],
                                     [expected, expected])

    def test_null_body_with_metadata_is_empty(self):
        """Keep the existing no-work contract for null callback bodies."""
        for binding, *_ in self._cases():
            with self.subTest(binding=binding):
                self.assertEqual(binding(data=Datum(value={
                    "body": None, "headers": {}, "statusCode": 200,
                }, type="json")).get_sdk_type(), [])

    def test_webhook_value_and_record_fields_remain_data(self):
        """Unwrap only the outer transport layer, not a notification's value field."""
        record = {"body": {"text": "record body"}, "headers": {"custom": "data"},
                  "value": [{"id": "nested"}], "id": "notification-1"}
        for binding in (RowChangeNotification,
                        DynamicNewMessageWebhookTriggerResponseSchema):
            for payload in (record, {"body": record, "headers": {}}):
                with self.subTest(binding=binding, payload=payload):
                    result = binding(data=Datum(value=payload,
                                                type="json")).get_sdk_type()
                    self.assertEqual(result[0].additional_properties, record)

    def test_dynamic_records_with_unknown_or_invalid_metadata_stay_intact(self):
        """Do not discard custom columns merely because a record contains body."""
        for record in (
            {"body": {"id": "nested"}, "headers": {}, "CustomColumn": 7},
            {"body": {"id": "nested"}, "headers": "custom column"},
            {"body": {"id": "nested"}, "statusCode": "custom column"},
            {"body": {"id": "nested"}, "statusCode": True},
        ):
            for binding in (SharePointItem, CdsItem, SalesforceItem):
                with self.subTest(binding=binding, record=record):
                    result = binding(data=Datum(value=record,
                                                type="json")).get_sdk_type()
                    self.assertEqual(result[0].dynamic_properties, record)

    def test_metadata_envelopes_keep_body_validation(self):
        """Reject invalid bodies rather than returning models full of null fields."""
        for binding, *_ in self._cases():
            for body in ("invalid body", 7, False):
                with self.subTest(binding=binding, body=body):
                    with self.assertRaises(ValueError):
                        binding(data=Datum(value={
                            "body": body, "headers": {},
                        }, type="json")).get_sdk_type()
