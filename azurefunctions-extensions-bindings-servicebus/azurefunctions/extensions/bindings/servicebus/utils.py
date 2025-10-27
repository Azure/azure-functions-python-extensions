#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import datetime
import struct
import uamqp
import uuid


_X_OPT_LOCK_TOKEN = b"x-opt-lock-token"
LOCK_TOKEN_LENGTH = 16

# AMQP format codes (subset)
FMT_NULL = 0x40
FMT_BOOL_TRUE = 0x41
FMT_BOOL_FALSE = 0x42
FMT_UINT = 0x70
FMT_INT = 0x71
FMT_LONG = 0x81
FMT_DOUBLE = 0x82
FMT_UTF8_SMALL = 0xA1
FMT_UTF8_LARGE = 0xB1
FMT_UUID = 0x98
FMT_MAP8 = 0xC1
FMT_MAP32 = 0xD1


def get_lock_token(message: bytes, index: int) -> str:
    # Get the lock token from the message
    lock_token_encoded = message[:index]

    # Convert the lock token to a UUID using the first 16 bytes
    # Use little-endian to match SDK
    lock_token_uuid = uuid.UUID(bytes_le=lock_token_encoded[:LOCK_TOKEN_LENGTH])

    return lock_token_uuid


def get_amqp_message(message: bytes):
    """
    Get the amqp message from the model_binding_data content
    and create the message.
    """
    amqp_message = message[LOCK_TOKEN_LENGTH:]
    decoded_message = uamqp.Message().decode_from_bytes(amqp_message)

    return decoded_message


def get_decoded_message(content: bytes):
    """
    First, find the end of the lock token. Then,
    get the lock token UUID and create the delivery
    annotations dictionary. Finally, get the amqp message
    and set the delivery annotations. Once the delivery
    annotations have been set, the amqp message is ready to
    return.
    """
    if content:
        try:
            index = content.find(_X_OPT_LOCK_TOKEN)

            lock_token = get_lock_token(content, index)
            delivery_anno_dict = {_X_OPT_LOCK_TOKEN: lock_token}

            decoded_message = get_amqp_message(content)
            decoded_message.delivery_annotations = delivery_anno_dict
            return decoded_message
        except Exception as e:
            raise ValueError(f"Failed to decode ServiceBus content: {e}") from e
    return None


def encode_amqp_value(value):
    if value is None:
        return bytes([FMT_NULL])
    elif isinstance(value, bool):
        return bytes([FMT_BOOL_TRUE if value else FMT_BOOL_FALSE])
    elif isinstance(value, int):
        # encode as int32 or int64 depending on value
        if -2**31 <= value < 2**31:
            return bytes([FMT_INT]) + struct.pack(">i", value)
        else:
            return bytes([FMT_LONG]) + struct.pack(">q", value)
    elif isinstance(value, float):
        return bytes([FMT_DOUBLE]) + struct.pack(">d", value)
    elif isinstance(value, str):
        utf8 = value.encode("utf-8")
        if len(utf8) < 256:
            return bytes([FMT_UTF8_SMALL, len(utf8)]) + utf8
        else:
            return bytes([FMT_UTF8_LARGE]) + struct.pack(">I", len(utf8)) + utf8
    elif isinstance(value, uuid.UUID):
        return bytes([FMT_UUID]) + value.bytes
    elif isinstance(value, datetime.timedelta):
        ticks = int(value.total_seconds() * 10_000_000)
        return encode_amqp_value(ticks)
    elif isinstance(value, datetime.datetime):
        # UTC ticks since 1970-01-01
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        ms = int((value - epoch).total_seconds() * 1000)
        return encode_amqp_value(ms)
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


# Encode map
def encode_amqp_map(dct):
    if not dct:
        return b""
    items_bytes = b"".join(
        encode_amqp_value(k) + encode_amqp_value(v) for k, v in dct.items()
    )
    size = len(items_bytes) + 1  # 1 byte for count
    count = len(dct) * 2
    if size < 256:
        return bytes([FMT_MAP8, size, count]) + items_bytes
    else:
        return (bytes([FMT_MAP32])
                + struct.pack(">I", size)
                + struct.pack(">I", count)
                + items_bytes)


# Main conversion function
def convert_to_bytestring(properties_to_modify: dict) -> bytes:
    return encode_amqp_map(properties_to_modify)
