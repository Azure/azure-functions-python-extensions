#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import uamqp
import uuid


_X_OPT_LOCK_TOKEN = b"x-opt-lock-token"


def get_lock_token(message: bytes, index: int) -> str:
    # Get the lock token from the message
    lock_token_encoded = message[:index]

    # Convert the lock token to a UUID using the first 16 bytes
    lock_token_uuid = uuid.UUID(bytes=lock_token_encoded[:16])

    return lock_token_uuid


def get_amqp_message(message: bytes, index: int):
    """
    Get the amqp message from the model_binding_data content
    and create the message.
    """
    amqp_message = message[index + len(b"x-opt-lock-token"):]
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
        index = content.find(b"x-opt-lock-token")

        lock_token = get_lock_token(content, index)
        delivery_anno_dict = {_X_OPT_LOCK_TOKEN: lock_token}

        decoded_message = get_amqp_message(content, index)
        decoded_message.delivery_annotations = delivery_anno_dict
        return decoded_message
    return None
