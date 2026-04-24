#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""
KafkaRecord type for raw Apache Kafka record binding.

Deserializes Protobuf-encoded ModelBindingData from the host-side Kafka Extension
into a Python object with full metadata access.
"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import List, Optional

from google.protobuf.internal.decoder import _DecodeVarint  # type: ignore
from google.protobuf.internal.wire_format import (  # type: ignore
    WIRETYPE_VARINT,
    WIRETYPE_LENGTH_DELIMITED,
)
from azurefunctions.extensions.base import Datum, SdkType


class KafkaTimestampType(IntEnum):
    """Defines the type of a Kafka record timestamp."""
    NotAvailable = 0
    CreateTime = 1
    LogAppendTime = 2


class KafkaTimestamp:
    """Represents the timestamp of a Kafka record."""

    __slots__ = ('unix_timestamp_ms', 'type')

    def __init__(self, unix_timestamp_ms: int, ts_type: KafkaTimestampType):
        self.unix_timestamp_ms = unix_timestamp_ms
        self.type = ts_type

    @property
    def datetime(self) -> datetime:
        """Returns the timestamp as a UTC datetime."""
        return datetime.fromtimestamp(
            self.unix_timestamp_ms / 1000.0, tz=timezone.utc
        )


class KafkaHeader:
    """Represents a single Kafka record header."""

    __slots__ = ('key', 'value')

    def __init__(self, key: str, value: Optional[bytes]):
        self.key = key
        self.value = value

    def get_value_as_string(self, encoding: str = 'utf-8') -> Optional[str]:
        """Returns the header value as a string, or None if value is None."""
        return self.value.decode(encoding) if self.value is not None else None


class KafkaRecord(SdkType):
    """
    Represents a raw Apache Kafka record with full metadata.
    Key and value are raw bytes — the user controls deserialization.
    """

    def __init__(self, *, data: Datum) -> None:
        self._data = data
        self._content = None
        self._parsed = False
        # Fields populated after parsing
        self._topic: str = ""
        self._partition: int = 0
        self._offset: int = 0
        self._key: Optional[bytes] = None
        self._value: Optional[bytes] = None
        self._timestamp: Optional[KafkaTimestamp] = None
        self._headers: List[KafkaHeader] = []
        self._leader_epoch: Optional[int] = None

        if self._data:
            self._content = data.content

    def get_sdk_type(self) -> 'KafkaRecord':
        """Deserialize Protobuf content and return self with populated fields."""
        if not self._parsed:
            if not self._content:
                raise ValueError(
                    f"Unable to create {self.__class__.__name__}: "
                    "content is empty."
                )
            self._decode_proto(self._content)
            self._parsed = True
        return self

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def partition(self) -> int:
        return self._partition

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def key(self) -> Optional[bytes]:
        return self._key

    @property
    def value(self) -> Optional[bytes]:
        return self._value

    @property
    def timestamp(self) -> Optional[KafkaTimestamp]:
        return self._timestamp

    @property
    def headers(self) -> List[KafkaHeader]:
        return self._headers

    @property
    def leader_epoch(self) -> Optional[int]:
        return self._leader_epoch

    def _decode_proto(self, content: bytes) -> None:
        """
        Decode KafkaRecordProto from Protobuf wire format.

        Proto schema field numbers:
          1: topic (string)
          2: partition (int32)
          3: offset (int64)
          4: key (optional bytes)
          5: value (optional bytes)
          6: timestamp (message)
          7: headers (repeated message)
          8: leader_epoch (optional int32)
        """
        pos = 0
        end = len(content)
        has_key = False
        has_value = False
        has_leader_epoch = False

        while pos < end:
            # Decode field tag
            tag, new_pos = _DecodeVarint(content, pos)
            pos = new_pos
            field_number = tag >> 3
            wire_type = tag & 0x7

            if field_number == 1 and wire_type == WIRETYPE_LENGTH_DELIMITED:
                # topic: string
                length, pos = _DecodeVarint(content, pos)
                self._topic = content[pos:pos + length].decode('utf-8')
                pos += length
            elif field_number == 2 and wire_type == WIRETYPE_VARINT:
                # partition: int32
                val, pos = _DecodeVarint(content, pos)
                self._partition = val
            elif field_number == 3 and wire_type == WIRETYPE_VARINT:
                # offset: int64
                val, pos = _DecodeVarint(content, pos)
                self._offset = val
            elif field_number == 4 and wire_type == WIRETYPE_LENGTH_DELIMITED:
                # key: optional bytes
                has_key = True
                length, pos = _DecodeVarint(content, pos)
                self._key = content[pos:pos + length]
                pos += length
            elif field_number == 5 and wire_type == WIRETYPE_LENGTH_DELIMITED:
                # value: optional bytes
                has_value = True
                length, pos = _DecodeVarint(content, pos)
                self._value = content[pos:pos + length]
                pos += length
            elif field_number == 6 and wire_type == WIRETYPE_LENGTH_DELIMITED:
                # timestamp: message
                length, pos = _DecodeVarint(content, pos)
                ts_end = pos + length
                ts_ms = 0
                ts_type = 0
                while pos < ts_end:
                    ts_tag, pos = _DecodeVarint(content, pos)
                    ts_field = ts_tag >> 3
                    if ts_field == 1:  # unix_timestamp_ms
                        ts_ms, pos = _DecodeVarint(content, pos)
                    elif ts_field == 2:  # type
                        ts_type, pos = _DecodeVarint(content, pos)
                    else:
                        # Skip unknown field
                        pos = self._skip_field(content, pos, ts_tag & 0x7)
                try:
                    ts_enum = KafkaTimestampType(ts_type)
                except ValueError:
                    ts_enum = KafkaTimestampType.NotAvailable
                self._timestamp = KafkaTimestamp(ts_ms, ts_enum)
            elif field_number == 7 and wire_type == WIRETYPE_LENGTH_DELIMITED:
                # headers: repeated message
                length, pos = _DecodeVarint(content, pos)
                h_end = pos + length
                h_key = ""
                h_value: Optional[bytes] = None
                h_has_value = False
                while pos < h_end:
                    h_tag, pos = _DecodeVarint(content, pos)
                    h_field = h_tag >> 3
                    if h_field == 1:  # key: string
                        h_len, pos = _DecodeVarint(content, pos)
                        h_key = content[pos:pos + h_len].decode('utf-8')
                        pos += h_len
                    elif h_field == 2:  # value: optional bytes
                        h_has_value = True
                        h_len, pos = _DecodeVarint(content, pos)
                        h_value = content[pos:pos + h_len]
                        pos += h_len
                    else:
                        pos = self._skip_field(content, pos, h_tag & 0x7)
                self._headers.append(
                    KafkaHeader(h_key, h_value if h_has_value else None)
                )
            elif field_number == 8 and wire_type == WIRETYPE_VARINT:
                # leader_epoch: optional int32
                has_leader_epoch = True
                val, pos = _DecodeVarint(content, pos)
                self._leader_epoch = val
            else:
                # Skip unknown field
                pos = self._skip_field(content, pos, wire_type)

        if not has_key:
            self._key = None
        if not has_value:
            self._value = None
        if not has_leader_epoch:
            self._leader_epoch = None

    @staticmethod
    def _skip_field(content: bytes, pos: int, wire_type: int) -> int:
        """Skip a protobuf field based on its wire type."""
        if wire_type == WIRETYPE_VARINT:
            _, pos = _DecodeVarint(content, pos)
        elif wire_type == WIRETYPE_LENGTH_DELIMITED:
            length, pos = _DecodeVarint(content, pos)
            pos += length
        elif wire_type == 5:  # 32-bit
            pos += 4
        elif wire_type == 1:  # 64-bit
            pos += 8
        return pos
