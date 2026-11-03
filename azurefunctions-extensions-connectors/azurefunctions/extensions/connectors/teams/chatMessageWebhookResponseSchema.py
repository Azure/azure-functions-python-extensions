#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind chat webhook notification envelopes, not full chat messages."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_chat_webhooks


class ChatMessageWebhookResponseSchema(
    ConnectorSdkType[list[models.ChatMessageWebhookResponseSchema]],
    models.ChatMessageWebhookResponseSchema,
):
    """Return notification envelopes with their value collections intact."""

    _deserialize = staticmethod(deserialize_chat_webhooks)
