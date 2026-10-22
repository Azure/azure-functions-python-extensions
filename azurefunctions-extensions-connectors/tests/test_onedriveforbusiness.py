#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Tests for OneDrive for Business metadata trigger SDK bindings."""

import copy
import json
import unittest
from dataclasses import field, fields, make_dataclass
from types import SimpleNamespace
from typing import Any, List
from unittest.mock import patch

import azure.connectors.onedriveforbusiness as models
import azurefunctions.extensions.connectors.onedriveforbusiness as onedrive
from azurefunctions.extensions.connectors.onedriveforbusiness import _deserialization
from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.connectors.onedriveforbusiness import (
    BlobMetadata,
    ConnectorConverter,
)


class TestOneDriveForBusinessBindings(unittest.TestCase):
    """Keep file metadata distinct from binary-content trigger payloads."""

    def test_public_binding_inherits_the_generated_metadata_model(self):
        """Expose the OneDrive SDK item rather than an unrelated blob model."""
        self.assertIn("BlobMetadata", onedrive.__all__)
        self.assertIn("ConnectorConverter", onedrive.__all__)
        self.assertTrue(issubclass(BlobMetadata, models.BlobMetadata))
        self.assertFalse(BlobMetadata.supports_deferred_binding())

    def test_converter_accepts_direct_and_list_annotations(self):
        """All supported annotations return a list of generated SDK items."""
        for annotation in (BlobMetadata, List[BlobMetadata], list[BlobMetadata]):
            with self.subTest(annotation=annotation):
                self.assertTrue(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )
                result = ConnectorConverter.decode(
                    data=Datum(value={"Id": "file-1"}, type="json"),
                    trigger_metadata=None,
                    pytype=annotation,
                )
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 1)
                self.assertIs(type(result[0]), models.BlobMetadata)
                self.assertEqual(result[0].id, "file-1")

    def test_converter_rejects_plain_sdk_models_as_binding_annotations(self):
        """Require the extension wrapper to opt into SDK conversion."""
        for annotation in (models.BlobMetadata, List[models.BlobMetadata]):
            with self.subTest(annotation=annotation):
                self.assertFalse(
                    ConnectorConverter.check_input_type_annotation(annotation),
                )

    def test_all_metadata_fields_deserialize_across_payload_shapes(self):
        """Honor all twelve SDK wire names without losing false or zero."""
        record = {
            "Id": "file-1",
            "Name": "Planning \u00e9quipe.docx",
            "NameNoExt": "Planning \u00e9quipe",
            "DisplayName": "Planning document",
            "Path": "/Documents/Planning \u00e9quipe.docx",
            "LastModified": "2026-10-21T10:00:00Z",
            "Size": 0,
            "MediaType": "application/octet-stream",
            "IsFolder": False,
            "ETag": '"version-1"',
            "FileLocator": "locator-1",
            "LastModifiedBy": "Example User",
        }
        original = copy.deepcopy(record)
        expected = models.BlobMetadata(
            id=record["Id"], name=record["Name"],
            name_no_ext=record["NameNoExt"], display_name=record["DisplayName"],
            path=record["Path"], last_modified=record["LastModified"],
            size=0, media_type=record["MediaType"], is_folder=False,
            e_tag=record["ETag"], file_locator=record["FileLocator"],
            last_modified_by=record["LastModifiedBy"],
        )
        for payload in (
            record,
            [record],
            {"body": record},
            {"body": [record]},
            {"value": [record]},
            {"body": {"@odata.context": "files", "value": [record]}},
            {"value": [record], "nextLink": "next-page"},
        ):
            serialized = json.dumps(payload, ensure_ascii=False)
            for value in (
                payload, serialized, serialized.encode("utf-8"),
                bytearray(serialized.encode("utf-8")),
            ):
                with self.subTest(value=value):
                    result = ConnectorConverter.decode(
                        data=Datum(value=value, type="json"),
                        trigger_metadata=None,
                        pytype=List[BlobMetadata],
                    )
                    self.assertEqual(result, [expected])
                    self.assertIs(type(result[0]), models.BlobMetadata)
                    self.assertIs(result[0].is_folder, False)
                    self.assertEqual(result[0].size, 0)
        self.assertEqual(record, original)

    def test_raw_source_array_preserves_file_order(self):
        """The two metadata trigger schemas return an array, not a page model."""
        result = BlobMetadata(data=Datum(value=[
            {"Id": "file-1", "Name": "First", "IsFolder": False},
            {"Id": "folder-2", "Name": "Second", "IsFolder": True},
        ], type="json")).get_sdk_type()
        self.assertEqual(
            [(item.id, item.name, item.is_folder) for item in result],
            [("file-1", "First", False), ("folder-2", "Second", True)],
        )

    def test_older_sdk_models_without_wire_metadata_are_supported(self):
        """Map all Pascal-case fields even when the SDK omits wire metadata."""
        legacy_model = make_dataclass("LegacyBlobMetadata", [
            (model_field.name, Any, field(default=None))
            for model_field in fields(models.BlobMetadata)
        ])
        record = {
            "Id": "file-1", "Name": "Planning.docx", "NameNoExt": "Planning",
            "DisplayName": "Planning", "Path": "/Planning.docx",
            "LastModified": "2026-10-21T10:00:00Z", "Size": 0,
            "MediaType": "application/octet-stream", "IsFolder": False,
            "ETag": "version-1", "FileLocator": "locator-1",
            "LastModifiedBy": "Example User",
        }
        expected = (
            "file-1", "Planning.docx", "Planning", "Planning", "/Planning.docx",
            "2026-10-21T10:00:00Z", 0, "application/octet-stream", False,
            "version-1", "locator-1", "Example User",
        )
        with patch.object(_deserialization, "BlobMetadata", legacy_model):
            result = BlobMetadata(data=Datum(value=record, type="json")).get_sdk_type()
        self.assertEqual(len(result), 1)
        self.assertEqual(
            tuple(getattr(result[0], model_field.name)
                  for model_field in fields(legacy_model)),
            expected,
        )

    def test_metadata_record_with_extra_value_field_is_not_a_batch(self):
        """An extra field must not hide the record's SDK metadata fields."""
        result = BlobMetadata(data=Datum(value={
            "Id": "file-1", "Name": "Planning", "value": [],
        }, type="json")).get_sdk_type()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "file-1")
        self.assertEqual(result[0].name, "Planning")

    def test_python_field_names_and_missing_optional_fields(self):
        """Keep Python-field fallback and absent SDK fields nullable."""
        result = BlobMetadata(data=Datum(value={
            "id": "file-1", "name_no_ext": "Planning", "e_tag": "",
            "last_modified_by": "", "is_folder": True,
        }, type="json")).get_sdk_type()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "file-1")
        self.assertEqual(result[0].name_no_ext, "Planning")
        self.assertEqual(result[0].e_tag, "")
        self.assertEqual(result[0].last_modified_by, "")
        self.assertIs(result[0].is_folder, True)
        self.assertIsNone(result[0].name)
        self.assertIsNone(result[0].size)

    def test_null_optional_fields_remain_null(self):
        """Do not replace explicit nulls with empty strings or zero."""
        result = BlobMetadata(data=Datum(value={
            "Id": "file-1", "Size": None, "IsFolder": None, "ETag": None,
        }, type="json")).get_sdk_type()
        self.assertIsNone(result[0].size)
        self.assertIsNone(result[0].is_folder)
        self.assertIsNone(result[0].e_tag)

    def test_empty_batches_and_null_callback_bodies(self):
        """No-work callbacks return an empty list rather than an empty model."""
        for payload in (
            [], {"body": []}, {"body": None}, {"value": []},
            {"value": None}, {"body": {"value": []}},
            {"body": {"@odata.context": "files", "value": None}},
        ):
            for value in (payload, json.dumps(payload)):
                with self.subTest(value=value):
                    self.assertEqual(BlobMetadata(data=Datum(
                        value=value, type="json",
                    )).get_sdk_type(), [])

    def test_poll_many_collections_flatten_records_and_source_arrays(self):
        """Preserve order across mixed single-record and source-batch events."""
        events = [
            json.dumps({"body": {"Id": "file-1"}}),
            json.dumps([{"Id": "file-2"}, {"Id": "file-3"}]),
            json.dumps({"body": {"value": [{"Id": "file-4"}]}}),
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
                    pytype=List[BlobMetadata],
                )
                self.assertEqual(
                    [item.id for item in result],
                    ["file-1", "file-2", "file-3", "file-4"],
                )

    def test_empty_poll_many_collections(self):
        """Empty transport collections contain no files."""
        for data_type, collection in (
            ("collection_string", SimpleNamespace(string=[])),
            ("collection_bytes", SimpleNamespace(bytes=[])),
        ):
            with self.subTest(data_type=data_type):
                self.assertEqual(BlobMetadata(data=Datum(
                    value=collection, type=data_type,
                )).get_sdk_type(), [])

    def test_invalid_json_envelopes_and_batch_members_raise(self):
        """Do not silently discard malformed source or transport events."""
        for value in (
            "not-json", b"\xff", 42, None, {"body": "invalid"},
            {"value": "invalid"}, {"value": [{"Id": "file-1"}, None]},
            {"body": [{"Id": "file-1"}, False]},
            [{"Id": "file-1"}, []],
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ConnectorConverter.decode(
                        data=Datum(value=value, type="json"),
                        trigger_metadata=None,
                        pytype=BlobMetadata,
                    )

    def test_binary_content_is_not_silently_bound_as_metadata(self):
        """Encoded file-content envelopes are not BlobMetadata records."""
        content = {"$content-type": "application/octet-stream", "$content": "AA=="}
        for payload in (content, {"body": content}, [content]):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "file content"):
                    BlobMetadata(data=Datum(
                        value=payload, type="json",
                    )).get_sdk_type()

    def test_missing_data_is_reported_consistently(self):
        """Match the existing converter and wrapper missing-input contracts."""
        self.assertIsNone(ConnectorConverter.decode(
            data=None, trigger_metadata=None, pytype=BlobMetadata,
        ))
        self.assertIsNone(ConnectorConverter.decode(
            data=Datum(value={}, type=None),
            trigger_metadata=None, pytype=BlobMetadata,
        ))
        with self.assertRaisesRegex(ValueError, "No data provided"):
            BlobMetadata(data=None).get_sdk_type()

    def test_properties_trigger_payloads_return_sdk_metadata(self):
        """Both plural operations use the same metadata item binding."""
        for operation in ("OnNewFilesV2", "OnUpdatedFilesV2"):
            with self.subTest(operation=operation):
                result = BlobMetadata(data=Datum(value=[{
                    "Id": operation, "Name": "Planning.docx",
                }], type="json")).get_sdk_type()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].id, operation)
                self.assertEqual(result[0].name, "Planning.docx")

    def test_sdk_trigger_registry_distinguishes_metadata_and_content(self):
        """Check registry evidence when exposed by the installed SDK version."""
        operations = getattr(models, "TRIGGER_OPERATIONS", None)
        if operations is None:
            self.skipTest("This SDK predates the OneDrive trigger registry.")
        for operation in ("OnNewFilesV2", "OnUpdatedFilesV2"):
            with self.subTest(operation=operation):
                self.assertEqual(
                    operations[operation]["callback_payload_type"], "BlobMetadata",
                )
        for operation in ("OnNewFileV2", "OnUpdatedFileV2"):
            with self.subTest(operation=operation):
                self.assertIsNone(
                    operations[operation]["callback_payload_type"],
                )
