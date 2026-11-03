#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind dynamic Teams new-message notifications."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_new_messages


class DynamicNewMessageWebhookTriggerResponseSchema(
    ConnectorSdkType[list[models.DynamicNewMessageWebhookTriggerResponseSchema]],
    models.DynamicNewMessageWebhookTriggerResponseSchema,
):
    """Return message models with every JSON field in additional_properties."""

    _deserialize = staticmethod(deserialize_new_messages)
