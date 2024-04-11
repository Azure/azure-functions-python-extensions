# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import unittest
from typing import List, Mapping
from unittest.mock import patch

from azurefunctions.extensions.base import meta, sdkType


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
        self.assertEqual(datum.python_value, "awesome string")
        self.assertEqual(datum.python_type, str)

        datum = meta.Datum(value=42, type="int")
        self.assertEqual(datum.python_value, 42)
        self.assertEqual(datum.python_type, int)

        datum = meta.Datum(value=43.2103, type="double")
        self.assertEqual(datum.python_value, 43.2103)
        self.assertEqual(datum.python_type, float)

        datum = meta.Datum(value="other", type="other")
        self.assertEqual(datum.python_value, "other")

    def test_datum_collections_python_value(self):
        class DatumCollectionString:
            def __init__(self, *args: List[str]):
                self.string = args

        datum = meta.Datum(
            value=DatumCollectionString("string 1", "string 2"),
            type="collection_string",
        )
        self.assertListEqual(datum.python_value, ["string 1", "string 2"])
        self.assertEqual(datum.python_type, list)

        class DatumCollectionBytes:
            def __init__(self, *args: List[bytes]):
                self.bytes = args

        datum = meta.Datum(
            value=DatumCollectionBytes(b"bytes 1", b"bytes 2"), type="collection_bytes"
        )
        self.assertListEqual(datum.python_value, [b"bytes 1", b"bytes 2"])
        self.assertEqual(datum.python_type, list)

        class DatumCollectionDouble:
            def __init__(self, *args: List[bytes]):
                self.double = args

        datum = meta.Datum(
            value=DatumCollectionDouble(43.2103, 45.601), type="collection_double"
        )
        self.assertListEqual(datum.python_value, [43.2103, 45.601])
        self.assertEqual(datum.python_type, list)

        class DatumCollectionSint64:
            def __init__(self, *args: List[int]):
                self.sint64 = args

        datum = meta.Datum(
            value=DatumCollectionSint64(1234567, 8901234), type="collection_sint64"
        )
        self.assertListEqual(datum.python_value, [1234567, 8901234])
        self.assertEqual(datum.python_type, list)

    def test_datum_json_python_value(self):
        # None
        datum = meta.Datum(value="null", type="json")
        self.assertEqual(datum.python_value, None)
        self.assertEqual(datum.python_type, type(None))

        # Int
        datum = meta.Datum(value="123", type="json")
        self.assertEqual(datum.python_value, 123)
        self.assertEqual(datum.python_type, int)

        # Float
        datum = meta.Datum(value="456.789", type="json")
        self.assertEqual(datum.python_value, 456.789)
        self.assertEqual(datum.python_type, float)

        # String
        datum = meta.Datum(value='"string in json"', type="json")
        self.assertEqual(datum.python_value, "string in json")
        self.assertEqual(datum.python_type, str)

        # List
        datum = meta.Datum(value='["a", "b", "c"]', type="json")
        self.assertListEqual(datum.python_value, ["a", "b", "c"])
        self.assertEqual(datum.python_type, list)

        # Object
        datum = meta.Datum(value='{"name": "awesome", "value": "cool"}', type="json")
        self.assertDictEqual(datum.python_value, {"name": "awesome", "value": "cool"})
        self.assertEqual(datum.python_type, dict)

        # Should ignore Newlines and Spaces
        datum = meta.Datum(
            value='{ "name" : "awesome",\n "value":  "cool"\n}', type="json"
        )
        self.assertDictEqual(datum.python_value, {"name": "awesome", "value": "cool"})
        self.assertEqual(datum.python_type, dict)

    def test_equals(self):
        str_datum = meta.Datum(value="awesome string", type="string")
        str_datum_copy = meta.Datum(value="awesome string", type="string")
        str_datum_wrong_copy = meta.Datum(value="not awesome string", type="string")
        self.assertFalse(str_datum.__eq__(dict))
        self.assertTrue(str_datum.__eq__(str_datum_copy))
        self.assertFalse(str_datum.__eq__(str_datum_wrong_copy))

    def test_hash(self):
        str_datum = meta.Datum(value="awesome string", type="string")
        datum_hash = str_datum.__hash__()
        self.assertIsInstance(datum_hash, int)

    def test_repr(self):
        str_datum = meta.Datum(value="awesome", type="string")
        self.assertEqual(str_datum.__repr__(), "<Datum string 'awesome'>")

        long_str_datum = meta.Datum(value="awesome string", type="string")
        self.assertEqual(long_str_datum.__repr__(), "<Datum string 'awesome s...>")

    def test_registry(self):
        registry = meta.get_binding_registry()
        self.assertIsInstance(registry, type(meta._ConverterMeta))
        self.assertIsNone(registry.get("test"))

        class MockIndexedFunction:
            _bindings = {}
            _trigger = None

        self.assertEqual(registry.get_raw_bindings(MockIndexedFunction, []), ([], {}))

        self.assertFalse(registry.check_supported_type(None))
        self.assertFalse(registry.check_supported_type("hello"))
        self.assertTrue(registry.check_supported_type(sdkType.SdkType))

        self.assertFalse(registry.has_trigger_support(MockIndexedFunction))

    def test_decode_typed_data(self):
        # Case 1: data is None
        self.assertIsNone(
            meta._BaseConverter._decode_typed_data(data=None, python_type=str)
        )

        # Case 2: data.type is model_binding_data
        datum_mbd = meta.Datum(value="{}", type="model_binding_data")
        self.assertEqual(
            meta._BaseConverter._decode_typed_data(datum_mbd, python_type=str), "{}"
        )

        # Case 3: data.type is None
        datum_none = meta.Datum(value="{}", type=None)
        self.assertIsNone(
            meta._BaseConverter._decode_typed_data(datum_none, python_type=str)
        )

        # Case 4: data.type is unsupported
        datum_unsupp = meta.Datum(value="{}", type=dict)
        with self.assertRaises(ValueError):
            meta._BaseConverter._decode_typed_data(datum_unsupp, python_type=str)

        # Case 5: can't coerce
        datum_coerce_fail = meta.Datum(value="{}", type="model_binding_data")
        with self.assertRaises(ValueError):
            meta._BaseConverter._decode_typed_data(
                datum_coerce_fail, python_type=(tuple, list, dict)
            )

        # Case 6: attempt coerce & fail
        datum_attempt_coerce = meta.Datum(value=1, type="model_binding_data")
        with self.assertRaises(ValueError):
            meta._BaseConverter._decode_typed_data(
                datum_attempt_coerce, python_type=dict
            )

        # Case 7: attempt to coerce and pass
        datum_coerce_pass = meta.Datum(value=1, type="model_binding_data")
        self.assertEqual(
            meta._BaseConverter._decode_typed_data(datum_coerce_pass, python_type=str),
            "1",
        )

    def test_decode_trigger_metadata_field(self):
        datum_mbd = meta.Datum(value="{}", type="model_binding_data")
        mock_trigger_metadata = {"key": datum_mbd}

        self.assertIsNone(
            meta._BaseConverter._decode_trigger_metadata_field(
                trigger_metadata=mock_trigger_metadata, field="fakeKey", python_type=str
            )
        )

        self.assertEqual(
            meta._BaseConverter._decode_trigger_metadata_field(
                trigger_metadata=mock_trigger_metadata, field="key", python_type=str
            ),
            "{}",
        )

    @patch(
        "azurefunctions.extensions.base.meta." "InConverter.__abstractmethods__", set()
    )
    def test_in_converter(self):
        class MockInConverter(meta.InConverter, binding="test1"):
            _sample = ""

        mock_converter = MockInConverter()
        self.assertIsNone(mock_converter.check_input_type_annotation(pytype=str))

        with self.assertRaises(NotImplementedError):
            mock_converter.decode(data=None, trigger_metadata={})

        self.assertFalse(mock_converter.has_implicit_output())

    @patch(
        "azurefunctions.extensions.base.meta." "OutConverter.__abstractmethods__", set()
    )
    def test_out_converter(self):
        class MockOutConverter(meta.OutConverter, binding="test2"):
            _sample = ""

        mock_converter = MockOutConverter()
        mock_converter.check_output_type_annotation(pytype=str)

        with self.assertRaises(NotImplementedError):
            mock_converter.encode(obj=None, expected_type=None)

    def test_get_registry(self):
        registry = meta.get_binding_registry()
        self.assertEqual(registry, meta._ConverterMeta)

    @patch(
        "azurefunctions.extensions.base.meta." "OutConverter.__abstractmethods__", set()
    )
    def test_converter_meta(self):
        class BindingNoneConverter(meta.OutConverter, binding=None):
            _sample = ""

        registry = meta.get_binding_registry()
        self.assertEqual(len(registry._bindings), 0)

        class BindingBlobConverter(meta.OutConverter, binding="blob"):
            _sample = ""

        registry = meta.get_binding_registry()
        self.assertEqual(len(registry._bindings), 1)
        self.assertIsNotNone(registry._bindings.get("blob"))
        self.assertEqual(registry._bindings.get("blob"), BindingBlobConverter)

        with self.assertRaises(RuntimeError):

            class BindingBlob2Converter(meta.OutConverter, binding="blob"):
                _sample = ""

        registry = meta.get_binding_registry()
        self.assertEqual(len(registry._bindings), 1)
        self.assertIsNotNone(registry._bindings.get("blob"))
        self.assertEqual(registry._bindings.get("blob"), BindingBlobConverter)

        class BindingServiceBusConverter(
            meta.OutConverter, binding="serviceBus", trigger="serviceBusTrigger"
        ):
            _sample = ""

        registry = meta.get_binding_registry()
        self.assertEqual(len(registry._bindings), 3)
        self.assertIsNotNone(registry._bindings.get("serviceBus"))
        self.assertEqual(
            registry._bindings.get("serviceBus"), BindingServiceBusConverter
        )
        self.assertIsNotNone(registry._bindings.get("serviceBusTrigger"))
        self.assertEqual(
            registry._bindings.get("serviceBusTrigger"), BindingServiceBusConverter
        )
