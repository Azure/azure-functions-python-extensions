#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic callback tests for Planner task trigger SDK bindings."""

import copy
import json
import unittest
from dataclasses import fields
from types import SimpleNamespace
from typing import List

import azure.connectors.planner as models
import azurefunctions.extensions.connectors.planner as planner
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.planner import (
    ConnectorConverter,
    GetTaskResponseV2,
)


class TestPlannerBindings(unittest.TestCase):
    """Keep generated task items, category models, and assignment JSON intact."""

    def test_public_binding_uses_generated_task_item(self):
        """Expose the trigger item model, not the V3 action or list envelope."""
        self.assertIn("GetTaskResponseV2", planner.__all__)
        self.assertIn("ConnectorConverter", planner.__all__)
        self.assertTrue(issubclass(GetTaskResponseV2, models.GetTaskResponseV2))
        self.assertFalse(GetTaskResponseV2.supports_deferred_binding())
        for annotation in (GetTaskResponseV2, List[GetTaskResponseV2],
                           list[GetTaskResponseV2]):
            with self.subTest(annotation=annotation):
                self.assertTrue(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )
                result = ConnectorConverter.decode(
                    data=Datum(value={"id": "task-1"}, type="json"),
                    trigger_metadata=None, pytype=annotation,
                )
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 1)
                self.assertIs(type(result[0]), models.GetTaskResponseV2)
                self.assertNotIsInstance(result[0], models.ListTasksResponse)
                self.assertEqual(result[0].id, "task-1")
        self.assertFalse(ConnectorConverter.check_input_type_annotation(
            models.GetTaskResponseV2,
        ))

    def test_all_task_fields_and_nested_json_across_payload_shapes(self):
        """Read all fourteen fields, including raw createdBy and assignments."""
        categories = {f"category{index}": index % 2 == 0 for index in range(1, 26)}
        categories["category25"] = None
        assignments = [{
            "userId": "user-1",
            "value": {
                "assignedBy": {"user": {"id": "assigner-1", "optional": None}},
                "assignedDateTime": "2026-10-21T10:00:00Z",
                "orderHint": "", "custom": False,
            },
        }]
        record = {
            "id": "task-1", "createdBy": {"user": {"id": "user-1"}, "extra": None},
            "planId": "plan-1", "bucketId": "bucket-1", "title": "Planning \u00e9quipe",
            "percentComplete": 0, "startDateTime": "2026-10-21T10:00:00Z",
            "createdDateTime": "2026-10-20T10:00:00Z", "dueDateTime": None,
            "hasDescription": False, "completedDateTime": None, "referenceCount": 0,
            "appliedCategories": categories, "_assignments": assignments,
        }
        original = copy.deepcopy(record)
        for payload in (
            record, [record], {"body": record}, {"body": [record]},
            {"value": [record]},
            {"body": {"@odata.context": "tasks", "value": [record],
                      "@odata.nextLink": "next-page"}},
        ):
            text = json.dumps(payload, ensure_ascii=False)
            for value in (
                payload, text, text.encode("utf-8"), bytearray(text.encode()),
            ):
                with self.subTest(value=value):
                    result = GetTaskResponseV2(data=Datum(
                        value=value, type="json",
                    )).get_sdk_type()
                    self.assertEqual(len(result), 1)
                    task = result[0]
                    self.assertIs(type(task), models.GetTaskResponseV2)
                    for model_field in fields(models.GetTaskResponseV2):
                        if model_field.name == "applied_categories":
                            continue
                        wire_name = model_field.metadata.get(
                            "wire_name", model_field.name,
                        )
                        self.assertEqual(
                            getattr(task, model_field.name), record[wire_name],
                        )
                    self.assertIs(
                        type(task.applied_categories), models.AppliedCategories,
                    )
                    for model_field in fields(models.AppliedCategories):
                        self.assertEqual(
                            getattr(task.applied_categories, model_field.name),
                            categories[model_field.name],
                        )
        self.assertEqual(record, original)

    def test_all_twenty_five_categories_are_available(self):
        """Do not stop at the older six-category subset."""
        categories = {f"category{index}": True for index in range(1, 26)}
        result = GetTaskResponseV2(data=Datum(value={
            "id": "task-1", "appliedCategories": categories,
        }, type="json")).get_sdk_type()
        self.assertEqual(len(fields(models.AppliedCategories)), 25)
        for key in categories:
            self.assertIs(getattr(result[0].applied_categories, key), True)

    def test_partial_and_null_optional_fields(self):
        """Absent and explicit null fields retain the SDK nullable contract."""
        result = GetTaskResponseV2(data=Datum(value={
            "id": "task-1", "title": "", "appliedCategories": {"category1": False},
            "_assignments": [],
        }, type="json")).get_sdk_type()
        task = result[0]
        self.assertEqual(task.title, "")
        self.assertEqual(task.assignments, [])
        self.assertIsNone(task.created_by)
        self.assertIsNone(task.percent_complete)
        self.assertIs(task.applied_categories.category1, False)
        self.assertIsNone(task.applied_categories.category25)
        null_task = GetTaskResponseV2(data=Datum(value={
            "id": "task-2", "appliedCategories": None, "_assignments": None,
            "createdBy": None, "hasDescription": None,
        }, type="json")).get_sdk_type()[0]
        self.assertIsNone(null_task.applied_categories)
        self.assertIsNone(null_task.assignments)
        self.assertIsNone(null_task.created_by)
        self.assertIsNone(null_task.has_description)

    def test_python_field_fallback_and_connector_assignment_precedence(self):
        """The connector _assignments array wins over a Graph-style object."""
        assignments = [{"userId": "user-1", "value": {"optional": None}}]
        for record in (
            {"id": "task-1", "assignments": assignments},
            {"id": "task-1", "_assignments": assignments,
             "assignments": {"graph-user": {"orderHint": "invalid-for-connector"}}},
        ):
            with self.subTest(record=record):
                self.assertEqual(GetTaskResponseV2(data=Datum(
                    value=record, type="json",
                )).get_sdk_type()[0].assignments, assignments)
        task = GetTaskResponseV2(data=Datum(value={
            "id": "task-1", "plan_id": "plan-1", "percent_complete": 100,
            "has_description": False,
        }, type="json")).get_sdk_type()[0]
        self.assertEqual(task.plan_id, "plan-1")
        self.assertEqual(task.percent_complete, 100)
        self.assertIs(task.has_description, False)

    def test_invalid_assignment_shapes_are_not_accepted_as_connector_arrays(self):
        """Reject native Graph objects and malformed assignment array members."""
        for assignments in ({"user-1": {}}, "user-1", [None], [{"userId": "1"}, False]):
            with self.subTest(assignments=assignments):
                with self.assertRaisesRegex(ValueError, "assignments"):
                    GetTaskResponseV2(data=Datum(value={
                        "id": "task-1", "_assignments": assignments,
                    }, type="json")).get_sdk_type()

    def test_poll_many_collections_preserve_order(self):
        """Flatten transport events and source batches without paging requests."""
        events = [
            {"body": {"id": "task-1"}},
            {"value": [{"id": "task-2"}, {"id": "task-3"}]},
            [{"id": "task-4"}],
        ]
        strings = [json.dumps(event) for event in events]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=strings)),
            ("collection_bytes", SimpleNamespace(
                bytes=[value.encode() for value in strings],
            )),
        ):
            with self.subTest(data_type=data_type):
                tasks = GetTaskResponseV2(data=Datum(
                    value=collection, type=data_type,
                )).get_sdk_type()
                self.assertEqual([task.id for task in tasks],
                                 ["task-1", "task-2", "task-3", "task-4"])

    def test_empty_batches_and_transport_collections(self):
        """No-work callbacks return an empty list, not a task with null fields."""
        for payload in ([], {"body": []}, {"body": None}, {"value": []},
                        {"body": {"@odata.context": "tasks", "value": None}}):
            with self.subTest(payload=payload):
                self.assertEqual(GetTaskResponseV2(data=Datum(
                    value=payload, type="json",
                )).get_sdk_type(), [])
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=[])),
            ("collection_bytes", SimpleNamespace(bytes=[])),
        ):
            self.assertEqual(GetTaskResponseV2(data=Datum(
                value=collection, type=data_type,
            )).get_sdk_type(), [])

    def test_record_value_and_body_fields_do_not_hide_task_data(self):
        """Extra record fields cannot masquerade as polling envelopes."""
        result = GetTaskResponseV2(data=Datum(value={
            "id": "task-1", "title": "Planning", "value": [],
            "body": {"custom": "field"},
        }, type="json")).get_sdk_type()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "task-1")
        self.assertEqual(result[0].title, "Planning")

    def test_invalid_source_payloads_raise(self):
        """Do not silently discard malformed JSON or batch members."""
        for payload in ("invalid", b"\xff", None, 1, {"body": "bad"},
                        {"value": "bad"}, {"value": [{"id": "valid"}, None]},
                        [{"id": "valid"}, False]):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    GetTaskResponseV2(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type()

    def test_missing_data_matches_existing_binding_contract(self):
        """Converter no-data returns None, while direct wrappers report an error."""
        self.assertIsNone(ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=GetTaskResponseV2,
        ))
        with self.assertRaisesRegex(ValueError, "No data provided"):
            GetTaskResponseV2(data=None).get_sdk_type()

    def test_all_three_trigger_operations_share_the_same_sdk_item_binding(self):
        """Verify trigger envelope names independently of the binding return shape."""
        registry = getattr(models, "TRIGGER_OPERATIONS", None)
        if registry is None:
            self.skipTest("This SDK does not expose a Planner trigger registry.")
        for operation in ("OnCompleteTask_V3", "OnNewTask_V3", "OnTaskAssignedToMe_V2"):
            with self.subTest(operation=operation):
                self.assertEqual(registry[operation]["method"], "get")
                self.assertEqual(
                    registry[operation]["callback_payload_type"], "ListTasksResponse",
                )
                result = GetTaskResponseV2(data=Datum(value={"body": {"value": [{
                    "id": operation, "percentComplete": 100,
                }]}}, type="json")).get_sdk_type()
                self.assertEqual(result[0].id, operation)
                self.assertEqual(result[0].percent_complete, 100)
