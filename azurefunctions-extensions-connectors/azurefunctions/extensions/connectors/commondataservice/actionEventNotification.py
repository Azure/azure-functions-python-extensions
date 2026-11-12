#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind dynamic BusinessEventsTrigger action-event notifications."""

from azure.connectors.commondataservice import ObjectEntity

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_notifications


class ActionEventNotification(ConnectorSdkType[list[ObjectEntity]], ObjectEntity):
    """Return SDK ObjectEntity records with action fields in additional_properties."""

    _deserialize = staticmethod(deserialize_notifications)
