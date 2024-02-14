# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Mapping, List
import unittest

from azure.functions.extension.base import meta


class TestMeta(unittest.TestCase):
    # Test Datum class
    def test_datum_single_level_python_value(self):
        datum: Mapping[str, meta.Datum] = meta.Datum(value=None, type="int")
        self.assertEqual(datum.python_value, None)
        self.assertEqual(datum.python_type, type(None))

        datum = meta.Datum(value=1, type=None)
        self.assertEqual(datum.python_value, None)
        self.assertEqual(datum.python_type, type(None))

        datum = meta.Datum(value=b"awesome bytes", type="bytes")
        self.assertEqual(datum.python_value, b"awesome bytes")
        self.assertEqual(datum.python_type, bytes)

        datum = meta.Datum(value="awesome string", type="string")
        self.assertEqual(datum.python_value, 'awesome string')
        self.assertEqual(datum.python_type, str)

        datum = meta.Datum(value=42, type="int")
        self.assertEqual(datum.python_value, 42)
        self.assertEqual(datum.python_type, int)

        datum = meta.Datum(value=43.2103, type="double")
        self.assertEqual(datum.python_value, 43.2103)
        self.assertEqual(datum.python_type, float)

    def test_datum_collections_python_value(self):
        class DatumCollectionString:
            def __init__(self, *args: List[str]):
                self.string = args
        datum = meta.Datum(value=DatumCollectionString("string 1", "string 2"),
                           type="collection_string")
        self.assertListEqual(datum.python_value, ["string 1", "string 2"])
        self.assertEqual(datum.python_type, list)

        class DatumCollectionBytes:
            def __init__(self, *args: List[bytes]):
                self.bytes = args
        datum = meta.Datum(value=DatumCollectionBytes(b"bytes 1", b"bytes 2"),
                           type="collection_bytes")
        self.assertListEqual(datum.python_value, [b"bytes 1", b"bytes 2"])
        self.assertEqual(datum.python_type, list)

        class DatumCollectionSint64:
            def __init__(self, *args: List[int]):
                self.sint64 = args
        datum = meta.Datum(value=DatumCollectionSint64(1234567, 8901234),
                           type="collection_sint64")
        self.assertListEqual(datum.python_value, [1234567, 8901234])
        self.assertEqual(datum.python_type, list)

    def test_datum_json_python_value(self):
        # None
        datum = meta.Datum(value='null',
                           type="json")
        self.assertEqual(datum.python_value, None)
        self.assertEqual(datum.python_type, type(None))

        # Int
        datum = meta.Datum(value='123',
                           type="json")
        self.assertEqual(datum.python_value, 123)
        self.assertEqual(datum.python_type, int)

        # Float
        datum = meta.Datum(value='456.789',
                           type="json")
        self.assertEqual(datum.python_value, 456.789)
        self.assertEqual(datum.python_type, float)

        # String
        datum = meta.Datum(value='"string in json"',
                           type="json")
        self.assertEqual(datum.python_value, "string in json")
        self.assertEqual(datum.python_type, str)

        # List
        datum = meta.Datum(value='["a", "b", "c"]',
                           type="json")
        self.assertListEqual(datum.python_value, ["a", "b", "c"])
        self.assertEqual(datum.python_type, list)

        # Object
        datum = meta.Datum(value='{"name": "awesome", "value": "cool"}',
                           type="json")
        self.assertDictEqual(datum.python_value, {
            "name": "awesome",
            "value": "cool"})
        self.assertEqual(datum.python_type, dict)

        # Should ignore Newlines and Spaces
        datum = meta.Datum(value='{ "name" : "awesome",\n "value":  "cool"\n}',
                           type="json")
        self.assertDictEqual(datum.python_value, {
            "name": "awesome",
            "value": "cool"})
        self.assertEqual(datum.python_type, dict)
