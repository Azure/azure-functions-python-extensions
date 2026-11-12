#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Teams channel polling messages."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_chat_messages


class ChatMessage(ConnectorSdkType[list[models.ChatMessage]], models.ChatMessage):
    """Return generated chat message items, retaining their nested JSON fields."""

    _deserialize = staticmethod(deserialize_chat_messages)
