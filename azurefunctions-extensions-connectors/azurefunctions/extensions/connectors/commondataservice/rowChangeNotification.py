#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind dynamic SubscribeWebhookTrigger row-change notifications."""

from azure.connectors.commondataservice import ObjectEntity

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_notifications


class RowChangeNotification(ConnectorSdkType[list[ObjectEntity]], ObjectEntity):
    """Return SDK ObjectEntity records with row fields in additional_properties."""

    _deserialize = staticmethod(deserialize_notifications)
