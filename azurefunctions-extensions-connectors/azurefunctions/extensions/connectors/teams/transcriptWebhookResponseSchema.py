#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Teams transcript-available notification metadata."""

import azure.connectors.teams as models

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_transcripts


class TranscriptWebhookResponseSchema(
    ConnectorSdkType[list[models.TranscriptWebhookResponseSchema]],
    models.TranscriptWebhookResponseSchema,
):
    """Return transcript metadata and content URLs without downloading content."""

    _deserialize = staticmethod(deserialize_transcripts)
