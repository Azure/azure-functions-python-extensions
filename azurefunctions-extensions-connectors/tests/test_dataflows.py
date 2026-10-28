#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Synthetic Dataflows refresh callbacks against the generated SDK model."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from dataclasses import fields
from types import SimpleNamespace
from typing import List

from azurefunctions.extensions.base import Datum

SDK_AVAILABLE = importlib.util.find_spec("azure.connectors.dataflows") is not None
if SDK_AVAILABLE:
    import azure.connectors.dataflows as models
    import azurefunctions.extensions.connectors.dataflows as dataflows


class TestDataflowsSdkAvailability(unittest.TestCase):
    """Keep the new SDK prerequisite isolated to the Dataflows namespace."""

    def test_missing_dataflows_sdk_has_actionable_error(self):
        """Do not prevent older connector imports when the new module is absent."""
        result = subprocess.run(
            [sys.executable, "-c", """
import sys
sys.modules['azure.connectors.dataflows'] = None
import azurefunctions.extensions.connectors.salesforce
try:
    import azurefunctions.extensions.connectors.dataflows
except ImportError as error:
    assert 'Dataflows bindings require' in str(error), str(error)
    assert 'azure.connectors.dataflows' in str(error), str(error)
    assert 'SDK main' in str(error), str(error)
else:
    raise AssertionError('Expected a missing Dataflows SDK prerequisite.')
import azurefunctions.extensions.connectors.planner
"""],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(SDK_AVAILABLE, "Dataflows bindings require SDK main (see sample).")
class TestDataflowsBindings(unittest.TestCase):
    """Keep refresh item fields, wire names, and transport cardinality intact."""

    def refresh_record(self):
        """Return a complete synthetic refresh record, not an action response."""
        return {
            "dataflowId": "flow-1", "dataflowName": "\u00e9quipe",
            "refreshType": "Scheduled", "startTime": "2026-10-28T01:00:00+05:30",
            "endTime": "2026-10-28T01:02:00+05:30", "status": "Success",
        }

    def decode(self, payload):
        """Exercise the Functions converter rather than constructing SDK models."""
        return dataflows.ConnectorConverter.decode(
            data=Datum(value=payload, type="json"), trigger_metadata=None,
            pytype=List[dataflows.RefreshModel],
        )

    def test_exports_annotations_and_exact_sdk_model(self):
        """Both accepted annotation forms return a list of SDK refresh items."""
        self.assertIn("RefreshModel", dataflows.__all__)
        self.assertIn("ConnectorConverter", dataflows.__all__)
        self.assertTrue(issubclass(dataflows.RefreshModel, models.RefreshModel))
        self.assertFalse(dataflows.RefreshModel.supports_deferred_binding())
        for annotation in (dataflows.RefreshModel, List[dataflows.RefreshModel],
                           list[dataflows.RefreshModel]):
            with self.subTest(annotation=annotation):
                self.assertTrue(dataflows.ConnectorConverter
                                .check_input_type_annotation(annotation))
                result = dataflows.ConnectorConverter.decode(
                    data=Datum(value=self.refresh_record(), type="json"),
                    trigger_metadata=None, pytype=annotation,
                )
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 1)
                self.assertIs(type(result[0]), models.RefreshModel)
                self.assertNotIsInstance(result[0], dataflows.RefreshModel)
                self.assertNotIsInstance(result[0], models.DataflowModel)
        self.assertFalse(dataflows.ConnectorConverter
                         .check_input_type_annotation(models.RefreshModel))

    def test_all_six_wire_fields_and_json_encodings(self):
        """Preserve every SDK field in direct records and sole-body callbacks."""
        record = self.refresh_record()
        original = copy.deepcopy(record)
        self.assertEqual({field.name for field in fields(models.RefreshModel)}, {
            "dataflow_id", "dataflow_name", "refresh_type", "start_time",
            "end_time", "status",
        })
        for payload in (record, {"body": record}):
            text = json.dumps(payload, ensure_ascii=False)
            for value in (payload, text, text.encode(), bytearray(text.encode())):
                with self.subTest(value=value):
                    result = self.decode(value)
                    self.assertEqual(len(result), 1)
                    for field in fields(models.RefreshModel):
                        actual = getattr(result[0], field.name)
                        self.assertEqual(actual, record[field.metadata.get(
                            "wire_name", field.name,
                        )])
                        self.assertIsInstance(actual, str)
        self.assertEqual(record, original)

    def test_python_field_fallback_and_wire_precedence(self):
        """Prefer present wire fields, including null, over Python fallbacks."""
        record = self.refresh_record()
        python_record = {field.name: record[field.metadata.get("wire_name", field.name)]
                         for field in fields(models.RefreshModel)}
        item = self.decode(python_record)[0]
        for field in fields(models.RefreshModel):
            self.assertEqual(getattr(item, field.name), python_record[field.name])
        both_names = {**python_record, **record, "dataflowId": None,
                      "dataflow_name": "wrong", "refresh_type": "wrong"}
        item = self.decode(both_names)[0]
        self.assertIsNone(item.dataflow_id)
        self.assertEqual(item.dataflow_name, record["dataflowName"])
        self.assertEqual(item.refresh_type, record["refreshType"])

    def test_optional_null_and_empty_fields_remain_distinct(self):
        """The SDK permits absent, null, and empty string values for all fields."""
        for value in (None, ""):
            record = {field.metadata.get("wire_name", field.name): value
                      for field in fields(models.RefreshModel)}
            with self.subTest(value=value):
                item = self.decode(record)[0]
                self.assertTrue(all(getattr(item, field.name) == value
                                    for field in fields(models.RefreshModel)))
        result = self.decode({})
        self.assertEqual(len(result), 1)
        self.assertTrue(all(getattr(result[0], field.name) is None
                            for field in fields(models.RefreshModel)))

    def test_failed_cancelled_and_future_status_values_are_data(self):
        """Refresh failure is callback data, not a deserialization exception."""
        for status in ("Success", "Failed", "Cancelled", "FutureStatus"):
            with self.subTest(status=status):
                item = self.decode({**self.refresh_record(), "status": status})[0]
                self.assertEqual(item.status, status)

    def test_transport_arrays_preserve_every_record(self):
        """Accept batched delivery without inventing a source value envelope."""
        records = [self.refresh_record(), {
            **self.refresh_record(), "dataflowId": "flow-2",
        }]
        for payload in (records, {"body": records}, json.dumps(records)):
            with self.subTest(payload=payload):
                result = self.decode(payload)
                self.assertEqual([item.dataflow_id for item in result],
                                 ["flow-1", "flow-2"])
                self.assertTrue(all(type(item) is models.RefreshModel
                                    for item in result))

    def test_transport_collections_preserve_order_and_empty_events(self):
        """Flatten Functions MANY events, retaining callback order."""
        events = [json.dumps(self.refresh_record()), json.dumps({"body": [{
            **self.refresh_record(), "dataflowId": "flow-2",
        }]}), json.dumps({"body": None}), json.dumps([])]
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=events)),
            ("collection_bytes", SimpleNamespace(
                bytes=[event.encode() for event in events],
            )),
        ):
            with self.subTest(data_type=data_type):
                result = dataflows.RefreshModel(data=Datum(
                    value=collection, type=data_type,
                )).get_sdk_type()
                self.assertEqual([item.dataflow_id for item in result],
                                 ["flow-1", "flow-2"])

    def test_empty_callbacks_and_transport_collections(self):
        """No-work transport events return no items rather than an empty model."""
        for payload in ([], {"body": []}, {"body": None}):
            self.assertEqual(self.decode(payload), [])
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=[])),
            ("collection_bytes", SimpleNamespace(bytes=[])),
        ):
            self.assertEqual(dataflows.RefreshModel(data=Datum(
                value=collection, type=data_type,
            )).get_sdk_type(), [])

    def test_body_and_value_named_extras_do_not_mask_refresh_fields(self):
        """The refresh record remains the source payload even with extra keys."""
        record = {**self.refresh_record(), "body": {"status": "wrong"},
                  "value": [{"status": "wrong"}]}
        for payload in (record, {"body": record}):
            item = self.decode(payload)[0]
            self.assertEqual(item.dataflow_id, "flow-1")
            self.assertEqual(item.status, "Success")

    def test_value_only_envelopes_are_not_the_refresh_contract(self):
        """Reject collection envelopes instead of producing empty refresh models."""
        for payload in ({"value": [self.refresh_record()]}, {"value": []},
                        {"value": None, "@odata.context": "refreshes"}):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "refresh record"):
                    self.decode(payload)

    def test_malformed_payloads_and_members_raise(self):
        """Reject malformed batches rather than silently dropping invalid entries."""
        for payload in ("invalid", b"\xff", None, False, 0, {"body": "bad"},
                        [self.refresh_record(), None], {"body": [False]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.decode(payload)

    def test_trigger_registry_is_a_single_refresh_polling_contract(self):
        """Check operation and parameter spelling without relying on it at runtime."""
        self.assertEqual(set(models.TRIGGER_OPERATIONS), {"OnRefreshComplete"})
        entry = models.TRIGGER_OPERATIONS["OnRefreshComplete"]
        self.assertEqual(entry["method"], "get")
        self.assertEqual(entry["callback_payload_type"], "RefreshModel")
        self.assertEqual(entry["required_parameters"], [
            "workspaceType", "groupIdForOnRefreshComplete",
            "dataflowIdForOnRefreshComplete",
        ])
        self.assertTrue(entry["path"].endswith(
            "/{dataflowIdForOnRefreshComplete}/onrefreshcomplete",
        ))

    def test_missing_data_follows_existing_converter_contract(self):
        """Keep converter no-data behavior separate from direct wrapper errors."""
        self.assertIsNone(dataflows.ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=dataflows.RefreshModel,
        ))
        with self.assertRaisesRegex(ValueError, "No data provided"):
            dataflows.RefreshModel(data=None).get_sdk_type()
