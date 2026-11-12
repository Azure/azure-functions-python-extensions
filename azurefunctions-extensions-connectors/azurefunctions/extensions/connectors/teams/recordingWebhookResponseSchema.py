#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Teams recording-available notification metadata."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_recordings


class RecordingWebhookResponseSchema(
    ConnectorSdkType[list[models.RecordingWebhookResponseSchema]],
    models.RecordingWebhookResponseSchema,
):
    """Return recording metadata and content URLs without downloading content."""

    _deserialize = staticmethod(deserialize_recordings)
