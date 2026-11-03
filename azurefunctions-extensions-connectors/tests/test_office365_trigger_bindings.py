#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Tests for Office 365 trigger item bindings and their return contracts."""

import json
import unittest
from types import SimpleNamespace
from typing import List

import azure.connectors.office365 as models
import azurefunctions.extensions.connectors.office365 as office365
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.office365 import (
    ConnectorConverter,
    GraphCalendarEventClientWithActionType,
    GraphCalendarEventListWithActionType,
)


class TestOffice365TriggerBindings(unittest.TestCase):
    """Check item types without changing existing list-returning bindings."""

    def test_changed_calendar_binding_is_exported_and_inherits_item_model(self):
        """Expose the generated item fields rather than envelope fields."""
        self.assertIn(
            "GraphCalendarEventClientWithActionType", office365.__all__,
        )
        self.assertTrue(issubclass(
            GraphCalendarEventClientWithActionType,
            models.GraphCalendarEventClientWithActionType,
        ))
        self.assertFalse(
            GraphCalendarEventClientWithActionType.supports_deferred_binding(),
        )

    def test_changed_calendar_binding_accepts_direct_and_list_annotations(self):
        """Accept the item binding through the generic connector converter."""
        for annotation in (
            GraphCalendarEventClientWithActionType,
            List[GraphCalendarEventClientWithActionType],
            list[GraphCalendarEventClientWithActionType],
        ):
            with self.subTest(annotation=annotation):
                self.assertTrue(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )
                self.assertIsNone(ConnectorConverter.decode(
                    data=None, trigger_metadata=None, pytype=annotation,
                ))

    def test_changed_calendar_binding_preserves_actions_and_wire_names(self):
        """Read both generated wire names and existing lower-camel callbacks."""
        for action_field, added_field, updated_field in (
            ("ActionType", "IsAdded", "IsUpdated"),
            ("actionType", "isAdded", "isUpdated"),
        ):
            for action in ("added", "updated", "deleted"):
                record = {
                    "id": "event-1",
                    "subject": "Planning",
                    action_field: action,
                    added_field: action == "added",
                    updated_field: action == "updated",
                    "startWithTimeZone": "2026-10-21T10:00:00Z",
                    "isAllDay": False,
                    "categories": ["Planning"],
                }
                for payload in (
                    record,
                    {"body": record},
                    {"value": [record]},
                    {"body": {"@odata.context": "calendar", "value": [record]}},
                ):
                    for value in (payload, json.dumps(payload)):
                        with self.subTest(action=action, value=value):
                            events = ConnectorConverter.decode(
                                data=Datum(value=value, type="json"),
                                trigger_metadata=None,
                                pytype=List[GraphCalendarEventClientWithActionType],
                            )
                            self.assertIsInstance(events, list)
                            self.assertEqual(len(events), 1)
                            event = events[0]
                            self.assertIsInstance(
                                event,
                                models.GraphCalendarEventClientWithActionType,
                            )
                            self.assertEqual(event.id, "event-1")
                            self.assertEqual(event.subject, "Planning")
                            self.assertEqual(event.action_type, action)
                            self.assertEqual(event.is_added, action == "added")
                            self.assertEqual(event.is_updated, action == "updated")
                            self.assertFalse(event.is_all_day)
                            self.assertEqual(event.categories, ["Planning"])
                            self.assertEqual(
                                event.start_with_time_zone,
                                "2026-10-21T10:00:00Z",
                            )

    def test_changed_calendar_binding_handles_poll_many_collections(self):
        """Flatten transport collections while keeping event action fields."""
        records = [
            {"id": "event-1", "ActionType": "added", "IsAdded": True},
            {"id": "event-2", "ActionType": "deleted", "IsAdded": False},
        ]
        events = [
            json.dumps({"body": records[0]}),
            json.dumps({"body": {"value": records[1:]}}),
        ]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=events)),
            ("collection_bytes", SimpleNamespace(
                bytes=[event.encode("utf-8") for event in events],
            )),
        ):
            with self.subTest(data_type=data_type):
                result = ConnectorConverter.decode(
                    data=Datum(value=collection, type=data_type),
                    trigger_metadata=None,
                    pytype=list[GraphCalendarEventClientWithActionType],
                )
                self.assertEqual(
                    [(event.id, event.action_type, event.is_added)
                     for event in result],
                    [("event-1", "added", True), ("event-2", "deleted", False)],
                )

    def test_changed_calendar_binding_matches_legacy_wrapper(self):
        """Keep the old import and list-returning behavior available."""
        for value in ([], None, [
            {"id": "event-1", "ActionType": "updated", "IsUpdated": True},
            {"id": "event-2", "ActionType": "deleted", "IsUpdated": False},
        ]):
            with self.subTest(value=value):
                data = Datum(value={"body": {"value": value}}, type="json")
                current = GraphCalendarEventClientWithActionType(
                    data=data,
                ).get_sdk_type()
                legacy = GraphCalendarEventListWithActionType(
                    data=data,
                ).get_sdk_type()
                self.assertIsInstance(current, list)
                self.assertIsInstance(legacy, list)
                self.assertEqual(current, legacy)
                self.assertEqual(len(current), len(value or []))

    def test_changed_calendar_binding_rejects_missing_and_invalid_payloads(self):
        """Report invalid input rather than returning empty success results."""
        for data, message in (
            (None, "No data provided"),
            (Datum(value="not-json", type="json"), "Invalid JSON payload"),
            (Datum(value={"body": []}, type="json"), "body must contain"),
        ):
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, message):
                    GraphCalendarEventClientWithActionType(
                        data=data,
                    ).get_sdk_type()

    def test_changed_calendar_binding_rejects_malformed_batch_members(self):
        """Reject whole batches instead of silently dropping malformed members."""
        record = {"id": "event-1", "ActionType": "added"}
        for invalid in (None, False, 0, "invalid", [], [record]):
            for members in ([record, invalid], [invalid, record], [invalid]):
                for payload in ({"value": members}, {"body": {"value": members}}):
                    for value in (payload, json.dumps(payload),
                                  json.dumps(payload).encode("utf-8")):
                        with self.subTest(invalid=invalid, value=value):
                            with self.assertRaisesRegex(ValueError, "batch item"):
                                ConnectorConverter.decode(
                                    data=Datum(value=value, type="json"),
                                    trigger_metadata=None,
                                    pytype=List[GraphCalendarEventClientWithActionType],
                                )

    def test_changed_calendar_binding_rejects_malformed_poll_many_members(self):
        """Apply strict validation inside every transport collection event."""
        events = [json.dumps({"id": "event-1"}),
                  json.dumps({"body": {"value": [{"id": "event-2"}, None]}})]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=events)),
            ("collection_bytes", SimpleNamespace(
                bytes=[event.encode("utf-8") for event in events],
            )),
        ):
            with self.subTest(data_type=data_type):
                with self.assertRaisesRegex(ValueError, "batch item"):
                    GraphCalendarEventClientWithActionType(
                        data=Datum(value=collection, type=data_type),
                    ).get_sdk_type()

    def test_changed_calendar_binding_rejects_invalid_collection_values(self):
        """Reject non-array collection values without changing legacy parsing."""
        for invalid in ("bad", "", {}, {"id": "event-1"}, False, 0, 1):
            for payload in ({"value": invalid}, {"body": {"value": invalid}}):
                for value in (payload, json.dumps(payload),
                              json.dumps(payload).encode("utf-8")):
                    with self.subTest(invalid=invalid, value=value):
                        data = Datum(value=value, type="json")
                        with self.assertRaisesRegex(ValueError, "value must contain"):
                            ConnectorConverter.decode(
                                data=data, trigger_metadata=None,
                                pytype=List[GraphCalendarEventClientWithActionType],
                            )
                        legacy = GraphCalendarEventListWithActionType(
                            data=data,
                        ).get_sdk_type()
                        self.assertEqual(len(legacy), 1)
                        self.assertIsNone(legacy[0].id)

    def test_changed_calendar_binding_rejects_invalid_poll_many_values(self):
        """Validate collection values inside string and byte transport events."""
        for invalid in ("bad", {}, False, 0):
            events = [json.dumps({"id": "event-1"}),
                      json.dumps({"body": {"value": invalid}})]
            for data_type, collection in (
                ("collection_string", SimpleNamespace(string=events)),
                ("collection_bytes", SimpleNamespace(
                    bytes=[event.encode("utf-8") for event in events],
                )),
            ):
                with self.subTest(invalid=invalid, data_type=data_type):
                    with self.assertRaisesRegex(ValueError, "value must contain"):
                        GraphCalendarEventClientWithActionType(
                            data=Datum(value=collection, type=data_type),
                        ).get_sdk_type()

    def test_legacy_calendar_wrapper_keeps_malformed_member_filtering(self):
        """Preserve the legacy wrapper's filtering for existing applications."""
        events = GraphCalendarEventListWithActionType(data=Datum(
            value={"body": {"value": [{"id": "event-1"}, None]}}, type="json",
        )).get_sdk_type()
        self.assertEqual([event.id for event in events], ["event-1"])

    def test_modern_trigger_operations_use_the_expected_item_bindings(self):
        """Cover the eight current SDK operations with their shared item types."""
        operation_groups = (
            (
                ("OnNewEmailV3", "OnFlaggedEmailV4", "OnNewMentionMeEmailV3",
                 "SharedMailboxOnNewEmailV2"),
                "TriggerBatchResponseGraphClientReceiveMessage",
                office365.GraphClientReceiveMessage,
                models.GraphClientReceiveMessage,
            ),
            (
                ("CalendarGetOnNewItemsV3", "CalendarGetOnUpdatedItemsV3",
                 "OnUpcomingEventsV3"),
                "GraphCalendarEventListClientReceive",
                office365.GraphCalendarEventClientReceive,
                models.GraphCalendarEventClientReceive,
            ),
            (
                ("CalendarGetOnChangedItemsV3",),
                "GraphCalendarEventListWithActionType",
                GraphCalendarEventClientWithActionType,
                models.GraphCalendarEventClientWithActionType,
            ),
        )
        for operations, envelope, binding_type, model_type in operation_groups:
            for operation in operations:
                with self.subTest(operation=operation):
                    self.assertEqual(
                        models.TRIGGER_OPERATIONS[operation]["callback_payload_type"],
                        envelope,
                    )
                    result = ConnectorConverter.decode(
                        data=Datum(value={"body": {"value": [{
                            "id": operation,
                            "subject": "Trigger event",
                        }]}}, type="json"),
                        trigger_metadata=None,
                        pytype=List[binding_type],
                    )
                    self.assertEqual(len(result), 1)
                    self.assertIsInstance(result[0], model_type)
                    self.assertEqual(result[0].id, operation)
                    self.assertEqual(result[0].subject, "Trigger event")
