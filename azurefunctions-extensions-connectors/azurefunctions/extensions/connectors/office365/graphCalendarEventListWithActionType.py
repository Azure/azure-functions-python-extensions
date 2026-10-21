#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.connectors.office365 import (
    GraphCalendarEventClientWithActionType,
    GraphCalendarEventListWithActionType as AzureGraphCalendarEventListWithActionType
)
from .._sdk_type import ConnectorSdkType
from ._deserialization import (
    deserialize_graph_calendar_events_with_action_type,
)


class GraphCalendarEventListWithActionType(
    ConnectorSdkType[list[GraphCalendarEventClientWithActionType]],
    AzureGraphCalendarEventListWithActionType,
):
    """Bind changed Microsoft Graph calendar events as a list of SDK items."""

    _deserialize = staticmethod(
        deserialize_graph_calendar_events_with_action_type
    )
