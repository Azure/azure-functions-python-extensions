#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import unittest
from types import SimpleNamespace
from typing import List

from azure.connectors.office365 import GraphCalendarEventClientWithActionType
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors._sdk_type import ConnectorSdkType
from azurefunctions.extensions.connectors.office365 import (
    ClientReceiveMessage,
    GraphClientReceiveMessage,
    GraphCalendarEventListWithActionType,
    GraphCalendarEventClientReceive,
    ConnectorConverter
)


def deserialize_future_connector(data: Datum) -> str:
    """Deserialize a stand-in future connector payload."""
    return data.value


class FutureConnectorSdkType(ConnectorSdkType[str]):
    """Represent a future connector without central converter registration."""

    _deserialize = staticmethod(deserialize_future_connector)


class TestConnectorConverter(unittest.TestCase):
    """Tests for the ConnectorConverter class."""

    def test_input_type_single(self):
        """Test that ClientReceiveMessage type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(ClientReceiveMessage))

    def test_input_type_list(self):
        """Test that List[ClientReceiveMessage] type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(List[ClientReceiveMessage]))

    def test_input_type_invalid(self):
        """Test that invalid type annotations are rejected"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertFalse(check_input_type(str))
        self.assertFalse(check_input_type(bytes))
        self.assertFalse(check_input_type(dict))
        self.assertFalse(check_input_type(List[str]))

    def test_input_type_none(self):
        """Test that None type annotation is rejected"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertFalse(check_input_type(None))

    def test_input_none(self):
        """Test that None data returns None"""
        result = ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=ClientReceiveMessage
        )
        self.assertIsNone(result)

    def test_graph_input_type_single(self):
        """Test that GraphClientReceiveMessage type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphClientReceiveMessage))

    def test_graph_input_type_list(self):
        """Test that List[GraphClientReceiveMessage] type annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(List[GraphClientReceiveMessage]))

    def test_graph_input_none(self):
        """Test that None data returns None for GraphClientReceiveMessage"""
        result = ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=GraphClientReceiveMessage
        )
        self.assertIsNone(result)

    def test_calendar_event_input_type_single(self):
        """Test that GraphCalendarEventListWithActionType annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphCalendarEventListWithActionType))

    def test_calendar_event_input_type_list(self):
        """Test that List[GraphCalendarEventListWithActionType] is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(
            check_input_type(List[GraphCalendarEventListWithActionType])
        )

    def test_calendar_event_input_none(self):
        """Test that None data returns None for GraphCalendarEventListWithActionType"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=GraphCalendarEventListWithActionType
        )
        self.assertIsNone(result)

    def test_calendar_event_client_receive_input_type_single(self):
        """Test that GraphCalendarEventClientReceive annotation is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(check_input_type(GraphCalendarEventClientReceive))

    def test_calendar_event_client_receive_input_type_list(self):
        """Test that List[GraphCalendarEventClientReceive] is accepted"""
        check_input_type = ConnectorConverter.check_input_type_annotation
        self.assertTrue(
            check_input_type(List[GraphCalendarEventClientReceive])
        )

    def test_calendar_event_client_receive_input_none(self):
        """Test that None data returns None for GraphCalendarEventClientReceive"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=GraphCalendarEventClientReceive
        )
        self.assertIsNone(result)

    def test_decode_with_list_type_annotation(self):
        """Test that decode works with List[Type] annotations"""
        # Test List[ClientReceiveMessage]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[ClientReceiveMessage]
        )
        self.assertIsNone(result)

        # Test List[GraphClientReceiveMessage]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphClientReceiveMessage]
        )
        self.assertIsNone(result)

        # Test List[GraphCalendarEventListWithActionType]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphCalendarEventListWithActionType]
        )
        self.assertIsNone(result)

        # Test List[GraphCalendarEventClientReceive]
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=List[GraphCalendarEventClientReceive]
        )
        self.assertIsNone(result)

    def test_decode_unsupported_type_returns_none(self):
        """Test that decode returns None for unsupported types"""
        result = ConnectorConverter.decode(
            data=None,
            trigger_metadata=None,
            pytype=str
        )
        self.assertIsNone(result)

    def test_decode_connector_sdk_type_without_registration(self):
        """Test that future connector types need no converter registration."""
        data = Datum(value="future-connector-value", type="json")

        result = ConnectorConverter.decode(
            data=data,
            trigger_metadata=None,
            pytype=FutureConnectorSdkType,
        )

        self.assertEqual(result, "future-connector-value")

    def test_decode_email_batch_with_metadata(self):
        """Preserve batch records when the envelope includes OData metadata."""
        body = {
            "@odata.context": "https://example.test/messages",
            "@odata.nextLink": "https://example.test/messages?skip=2",
            "value": [
                {"id": "message-1", "subject": "First", "importance": "high"},
                {"id": "message-2", "subject": "Second", "importance": "low"},
            ],
        }
        for payload in (body, {"body": body}, json.dumps({"body": body})):
            with self.subTest(payload=payload):
                messages = ConnectorConverter.decode(
                    data=Datum(value=payload, type="json"),
                    trigger_metadata=None,
                    pytype=List[ClientReceiveMessage],
                )

                self.assertEqual(len(messages), 2)
                self.assertEqual(
                    [(message.id, message.subject, message.importance)
                     for message in messages],
                    [("message-1", "First", 2), ("message-2", "Second", 0)],
                )

    def test_decode_empty_email_batch_with_metadata(self):
        """An empty or null batch with metadata contains no messages."""
        for value in ([], None):
            with self.subTest(value=value):
                messages = ConnectorConverter.decode(
                    data=Datum(
                        value={"body": {
                            "@odata.context": "messages", "value": value,
                        }},
                        type="json",
                    ),
                    trigger_metadata=None,
                    pytype=List[ClientReceiveMessage],
                )

                self.assertEqual(messages, [])

    def test_decode_single_email_with_scalar_value(self):
        """A scalar value property does not turn a message into a batch."""
        messages = ConnectorConverter.decode(
            data=Datum(
                value={"body": {"id": "message-1", "value": "custom-value"}},
                type="json",
            ),
            trigger_metadata=None,
            pytype=List[ClientReceiveMessage],
        )

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, "message-1")

    def test_decode_record_body_is_not_callback_envelope(self):
        """Preserve a record's own body in direct and wrapped payloads."""
        for body in ("Hello", None, {"contentType": "text", "content": "Hello"}):
            record = {"id": "message-1", "subject": "Test", "body": body}
            for payload in (record, {"body": record}):
                for value in (payload, json.dumps(payload)):
                    with self.subTest(body=body, value=value):
                        messages = ConnectorConverter.decode(
                            data=Datum(value=value, type="json"),
                            trigger_metadata=None,
                            pytype=List[ClientReceiveMessage],
                        )

                        self.assertEqual(len(messages), 1)
                        self.assertEqual(messages[0].id, record["id"])
                        self.assertEqual(messages[0].subject, record["subject"])
                        self.assertEqual(messages[0].body, body)

    def test_decode_polling_records_preserve_body(self):
        """Poll collections preserve direct and wrapped record bodies."""
        records = [
            {"id": "message-1", "body": "Hello"},
            {"id": "message-2", "body": None},
            {"id": "message-3", "body": {"content": "Hello"}},
        ]
        for wrapped in (False, True):
            for data_type in ("collection_string", "collection_bytes"):
                events = [
                    json.dumps({"body": record} if wrapped else record)
                    for record in records
                ]
                collection = (
                    SimpleNamespace(string=events)
                    if data_type == "collection_string"
                    else SimpleNamespace(bytes=[event.encode() for event in events])
                )
                with self.subTest(wrapped=wrapped, data_type=data_type):
                    messages = ConnectorConverter.decode(
                        data=Datum(value=collection, type=data_type),
                        trigger_metadata=None,
                        pytype=List[ClientReceiveMessage],
                    )

                    self.assertEqual(
                        [(message.id, message.body) for message in messages],
                        [(record["id"], record["body"]) for record in records],
                    )

    def test_decode_null_callback_body(self):
        """A null callback body still contains no records."""
        messages = ConnectorConverter.decode(
            data=Datum(value={"body": None}, type="json"),
            trigger_metadata=None,
            pytype=List[ClientReceiveMessage],
        )

        self.assertEqual(messages, [])

    def test_decode_invalid_callback_body(self):
        """A callback body must still be an object or null."""
        for body in ("Hello", []):
            with self.subTest(body=body):
                with self.assertRaisesRegex(
                    ValueError, "Connector payload body must contain a JSON object",
                ):
                    ConnectorConverter.decode(
                        data=Datum(value={"body": body}, type="json"),
                        trigger_metadata=None,
                        pytype=List[ClientReceiveMessage],
                    )

    def test_decode_polling_email_collection(self):
        """Deserialize each Poll MANY event, including nested source batches."""
        events = [
            json.dumps({"body": {"id": "message-1", "subject": "First"}}),
            json.dumps({"body": {
                "@odata.context": "messages",
                "value": [
                    {"id": "message-2", "subject": "Second"},
                    {"id": "message-3", "subject": "Third"},
                ],
            }}),
        ]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=events)),
            ("collection_bytes", SimpleNamespace(
                bytes=[event.encode("utf-8") for event in events],
            )),
        ):
            with self.subTest(data_type=data_type):
                messages = ConnectorConverter.decode(
                    data=Datum(value=collection, type=data_type),
                    trigger_metadata=None,
                    pytype=List[ClientReceiveMessage],
                )

                self.assertEqual(
                    [(message.id, message.subject) for message in messages],
                    [("message-1", "First"), ("message-2", "Second"),
                     ("message-3", "Third")],
                )

    def test_decode_empty_polling_email_collection(self):
        """An empty transport collection contains no messages."""
        messages = ConnectorConverter.decode(
            data=Datum(
                value=SimpleNamespace(string=[]), type="collection_string",
            ),
            trigger_metadata=None,
            pytype=List[ClientReceiveMessage],
        )

        self.assertEqual(messages, [])

    def test_decode_changed_calendar_events_returns_list(self):
        """Keep changed events indexable and iterable for shipped handlers."""
        events = [
            {"id": "event-1", "subject": "Planning",
             "actionType": "added", "isAdded": True},
            {"id": "event-2", "subject": "Review",
             "actionType": "updated", "isUpdated": True},
        ]
        for annotation in (
            GraphCalendarEventListWithActionType,
            List[GraphCalendarEventListWithActionType],
            list[GraphCalendarEventListWithActionType],
        ):
            for items in (events[:1], events, []):
                payloads = [
                    {"body": {"@odata.context": "calendar", "value": items}},
                ]
                if len(items) == 1:
                    payloads.append({"body": items[0]})
                for payload in payloads:
                    with self.subTest(annotation=annotation, payload=payload):
                        result = ConnectorConverter.decode(
                            data=Datum(value=json.dumps(payload), type="json"),
                            trigger_metadata=None,
                            pytype=annotation,
                        )

                        self.assertIsInstance(result, list)
                        self.assertEqual(len(result), len(items))
                        for event in result:
                            self.assertIsInstance(
                                event, GraphCalendarEventClientWithActionType,
                            )
                        self.assertEqual(
                            [(event.id, event.subject, event.action_type)
                             for event in result],
                            [(item["id"], item["subject"], item["actionType"])
                             for item in items],
                        )
                        if items:
                            self.assertTrue(result[0].is_added)
                        if len(items) == 2:
                            self.assertTrue(result[1].is_updated)


if __name__ == "__main__":
    unittest.main()
