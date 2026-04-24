#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import struct
import unittest
from typing import List, Optional

from azurefunctions.extensions.base import Datum
from azurefunctions.extensions.bindings.kafka import (
    KafkaRecord,
    KafkaRecordConverter,
    KafkaHeader,
    KafkaTimestamp,
    KafkaTimestampType,
)


# ---- Protobuf encoding helpers (mirrors host-side KafkaRecordProtobufSerializer) ----

def _encode_varint(value: int) -> bytes:
    """Encode an unsigned varint."""
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def _encode_tag(field_number: int, wire_type: int) -> bytes:
    return _encode_varint((field_number << 3) | wire_type)


def _encode_string(field_number: int, value: str) -> bytes:
    data = value.encode('utf-8')
    return _encode_tag(field_number, 2) + _encode_varint(len(data)) + data


def _encode_bytes(field_number: int, value: bytes) -> bytes:
    return _encode_tag(field_number, 2) + _encode_varint(len(value)) + value


def _encode_varint_field(field_number: int, value: int) -> bytes:
    return _encode_tag(field_number, 0) + _encode_varint(value)


def _encode_message(field_number: int, data: bytes) -> bytes:
    return _encode_tag(field_number, 2) + _encode_varint(len(data)) + data


def encode_kafka_record_proto(
    topic: str = "",
    partition: int = 0,
    offset: int = 0,
    key: Optional[bytes] = None,
    value: Optional[bytes] = None,
    timestamp_ms: int = 0,
    timestamp_type: int = 0,
    headers: Optional[List[tuple]] = None,
    leader_epoch: Optional[int] = None,
) -> bytes:
    """Encode a KafkaRecordProto message matching the host-side serializer output."""
    result = bytearray()

    if topic:
        result += _encode_string(1, topic)
    if partition:
        result += _encode_varint_field(2, partition)
    if offset:
        result += _encode_varint_field(3, offset)
    if key is not None:
        result += _encode_bytes(4, key)
    if value is not None:
        result += _encode_bytes(5, value)

    # Timestamp message (field 6)
    ts_data = _encode_varint_field(1, timestamp_ms) + _encode_varint_field(2, timestamp_type)
    result += _encode_message(6, ts_data)

    # Headers (field 7, repeated)
    if headers:
        for h_key, h_value in headers:
            h_data = _encode_string(1, h_key)
            if h_value is not None:
                h_data += _encode_bytes(2, h_value)
            result += _encode_message(7, h_data)

    if leader_epoch is not None:
        result += _encode_varint_field(8, leader_epoch)

    return bytes(result)


# ---- Mock classes (same pattern as EventHub tests) ----

class MockMBD:
    """Mock ModelBindingData."""
    def __init__(self, version: str, source: str, content_type: str, content: bytes):
        self.version = version
        self.source = source
        self.content_type = content_type
        self.content = content


class MockCMBD:
    """Mock CollectionModelBindingData."""
    def __init__(self, model_binding_data_list: List[MockMBD]):
        self.model_binding_data = model_binding_data_list


# ---- Tests ----

class TestKafkaRecord(unittest.TestCase):
    """Tests for KafkaRecord Protobuf deserialization."""

    def _make_datum_mbd(self, proto_bytes: bytes) -> Datum:
        mbd = MockMBD(
            version="1.0",
            source="AzureKafkaRecord",
            content_type="application/x-protobuf",
            content=proto_bytes,
        )
        return Datum(value=mbd, type="model_binding_data")

    def test_full_record(self):
        proto = encode_kafka_record_proto(
            topic="my-topic",
            partition=3,
            offset=12345,
            key=b"my-key",
            value=b'{"name":"test"}',
            timestamp_ms=1700000000000,
            timestamp_type=1,
            headers=[("trace-id", b"trace-abc")],
            leader_epoch=7,
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertIsInstance(result, KafkaRecord)
        self.assertEqual(result.topic, "my-topic")
        self.assertEqual(result.partition, 3)
        self.assertEqual(result.offset, 12345)
        self.assertEqual(result.key, b"my-key")
        self.assertEqual(result.value, b'{"name":"test"}')
        self.assertEqual(result.timestamp.unix_timestamp_ms, 1700000000000)
        self.assertEqual(result.timestamp.type, KafkaTimestampType.CreateTime)
        self.assertEqual(result.leader_epoch, 7)
        self.assertEqual(len(result.headers), 1)
        self.assertEqual(result.headers[0].key, "trace-id")
        self.assertEqual(result.headers[0].get_value_as_string(), "trace-abc")

    def test_null_key_and_value(self):
        proto = encode_kafka_record_proto(
            topic="test-topic",
            partition=0,
            offset=100,
            timestamp_ms=1700000000000,
            timestamp_type=0,
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertIsNone(result.key)
        self.assertIsNone(result.value)

    def test_no_leader_epoch(self):
        proto = encode_kafka_record_proto(
            topic="test-topic",
            value=b"test",
            timestamp_ms=0,
            timestamp_type=0,
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertIsNone(result.leader_epoch)

    def test_unknown_timestamp_type(self):
        proto = encode_kafka_record_proto(
            topic="test-topic",
            value=b"test",
            timestamp_ms=1700000000000,
            timestamp_type=99,
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertEqual(result.timestamp.type, KafkaTimestampType.NotAvailable)

    def test_multiple_headers(self):
        proto = encode_kafka_record_proto(
            topic="test-topic",
            value=b"test",
            timestamp_ms=0,
            timestamp_type=0,
            headers=[
                ("correlation-id", b"abc-123"),
                ("null-value-header", None),
            ],
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertEqual(len(result.headers), 2)
        self.assertEqual(result.headers[0].key, "correlation-id")
        self.assertEqual(result.headers[0].get_value_as_string(), "abc-123")
        self.assertEqual(result.headers[1].key, "null-value-header")
        self.assertIsNone(result.headers[1].value)

    def test_timestamp_datetime(self):
        proto = encode_kafka_record_proto(
            topic="test-topic",
            value=b"test",
            timestamp_ms=1700000000000,
            timestamp_type=2,
        )
        datum = self._make_datum_mbd(proto)
        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertEqual(result.timestamp.type, KafkaTimestampType.LogAppendTime)
        dt = result.timestamp.datetime
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 11)

    def test_batch_collection(self):
        proto = encode_kafka_record_proto(
            topic="batch-topic",
            partition=1,
            offset=42,
            value=b"msg1",
            timestamp_ms=1700000000000,
            timestamp_type=1,
        )
        mbd = MockMBD("1.0", "AzureKafkaRecord", "application/x-protobuf", proto)
        datum = Datum(value=MockCMBD([mbd, mbd]), type="collection_model_binding_data")

        result = KafkaRecordConverter.decode(
            data=datum, trigger_metadata=None, pytype=KafkaRecord
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].topic, "batch-topic")
        self.assertEqual(result[1].offset, 42)

    def test_none_data(self):
        result = KafkaRecordConverter.decode(
            data=None, trigger_metadata=None, pytype=KafkaRecord
        )
        self.assertIsNone(result)

    def test_invalid_data_type(self):
        datum = Datum(value="hello", type="str")
        with self.assertRaises(ValueError):
            KafkaRecordConverter.decode(
                data=datum, trigger_metadata=None, pytype=KafkaRecord
            )

    def test_input_type_annotation(self):
        self.assertTrue(KafkaRecordConverter.check_input_type_annotation(KafkaRecord))
        self.assertFalse(KafkaRecordConverter.check_input_type_annotation(str))
        self.assertTrue(KafkaRecordConverter.check_input_type_annotation(List[KafkaRecord]))
        self.assertFalse(KafkaRecordConverter.check_input_type_annotation(None))

    def test_header_get_value_as_string_none(self):
        header = KafkaHeader("key", None)
        self.assertIsNone(header.get_value_as_string())


if __name__ == "__main__":
    unittest.main()
