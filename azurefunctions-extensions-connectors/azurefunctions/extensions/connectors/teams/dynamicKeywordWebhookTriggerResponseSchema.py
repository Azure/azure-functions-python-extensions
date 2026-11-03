#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind dynamic Teams keyword notifications."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_keywords


class DynamicKeywordWebhookTriggerResponseSchema(
    ConnectorSdkType[list[models.DynamicKeywordWebhookTriggerResponseSchema]],
    models.DynamicKeywordWebhookTriggerResponseSchema,
):
    """Return keyword models with every JSON field in additional_properties."""

    _deserialize = staticmethod(deserialize_keywords)
