#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind dynamic Teams mention notifications."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_mentions


class DynamicAtMentionWebhookTriggerResponseSchema(
    ConnectorSdkType[list[models.DynamicAtMentionWebhookTriggerResponseSchema]],
    models.DynamicAtMentionWebhookTriggerResponseSchema,
):
    """Return mention models with every JSON field in additional_properties."""

    _deserialize = staticmethod(deserialize_mentions)
