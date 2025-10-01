#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
import unittest
import datetime
import uuid
from azurefunctions.extensions.bindings.servicebus.utils import (encode_amqp_value,
                                                                 encode_amqp_map,
                                                                 convert_to_bytestring)


class TestAmqpEncoding(unittest.TestCase):

    def test_encode_none(self):
        result = encode_amqp_value(None)
        self.assertEqual(result, bytes([0x40]))  # FMT_NULL

    def test_encode_bool(self):
        self.assertEqual(encode_amqp_value(True), bytes([0x41]))   # FMT_BOOL_TRUE
        self.assertEqual(encode_amqp_value(False), bytes([0x42]))  # FMT_BOOL_FALSE

    def test_encode_int(self):
        # Small int
        small_int = 123
        result = encode_amqp_value(small_int)
        self.assertEqual(result[0], 0x71)  # FMT_INT
        self.assertEqual(int.from_bytes(result[1:], "big", signed=True), small_int)

        # Large int
        large_int = 2**40
        result = encode_amqp_value(large_int)
        self.assertEqual(result[0], 0x81)  # FMT_LONG
        self.assertEqual(int.from_bytes(result[1:], "big", signed=True), large_int)

    def test_encode_float(self):
        val = 3.1415
        result = encode_amqp_value(val)
        self.assertEqual(result[0], 0x82)  # FMT_DOUBLE

    def test_encode_str(self):
        s = "hello"
        result = encode_amqp_value(s)
        self.assertIn(result[0], (0xA1, 0xB1))  # FMT_UTF8_SMALL or LARGE

    def test_encode_uuid(self):
        u = uuid.uuid4()
        result = encode_amqp_value(u)
        self.assertEqual(result[0], 0x98)  # FMT_UUID
        self.assertEqual(result[1:], u.bytes)

    def test_encode_timedelta(self):
        td = datetime.timedelta(seconds=5)
        result = encode_amqp_value(td)
        # Should encode as int ticks
        ticks = int(td.total_seconds() * 10_000_000)
        encoded_ticks = int.from_bytes(result[1:], "big", signed=True)
        self.assertEqual(encoded_ticks, ticks)

    def test_encode_datetime(self):
        dt = datetime.datetime(1970, 1, 2, tzinfo=datetime.timezone.utc)
        result = encode_amqp_value(dt)
        # 1 day in ms = 86400000
        ms = int((dt - datetime.datetime(
            1970,
            1,
            1,
            tzinfo=datetime.timezone.utc)).total_seconds() * 1000)
        encoded_ms = int.from_bytes(result[1:], "big", signed=True)
        self.assertEqual(encoded_ms, ms)

    def test_encode_unsupported_type(self):
        with self.assertRaises(TypeError):
            encode_amqp_value(object())

    def test_encode_amqp_map_empty(self):
        result = encode_amqp_map({})
        self.assertEqual(result, bytes([0xC1, 1, 0]))  # FMT_MAP8, 1 byte size, 0 pairs

    def test_encode_amqp_map_scalars(self):
        data = {
            "a": 1,
            "b": True,
            "c": "hi"
        }
        result = convert_to_bytestring(data)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_encode_application_properties_empty(self):
        data = {}
        result = convert_to_bytestring(data)
        self.assertIsInstance(result, bytes)
        self.assertEqual(len(result), 0)
