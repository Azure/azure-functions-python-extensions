#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.connectors.office365 import (
    GraphCalendarEventClientReceive as AzureGraphCalendarEventClientReceive
)
from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_graph_calendar_events


class GraphCalendarEventClientReceive(
    ConnectorSdkType[list[AzureGraphCalendarEventClientReceive]],
    AzureGraphCalendarEventClientReceive,
):
    """Azure Functions binding for Microsoft Graph calendar events."""

    _deserialize = staticmethod(deserialize_graph_calendar_events)
