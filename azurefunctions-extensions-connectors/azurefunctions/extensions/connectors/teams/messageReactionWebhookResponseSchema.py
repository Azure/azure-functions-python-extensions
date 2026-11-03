#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Teams reaction webhook notification metadata."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_reactions


class MessageReactionWebhookResponseSchema(
    ConnectorSdkType[list[models.MessageReactionWebhookResponseSchema]],
    models.MessageReactionWebhookResponseSchema,
):
    """Return generated reaction notification models."""

    _deserialize = staticmethod(deserialize_reactions)
