#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.connectors.office365 import (
    GraphCalendarEventListWithActionType as AzureGraphCalendarEventListWithActionType
)
from .._sdk_type import ConnectorSdkType
from ._deserialization import (
    deserialize_graph_calendar_events_with_action_type,
)


class GraphCalendarEventListWithActionType(
    ConnectorSdkType[AzureGraphCalendarEventListWithActionType],
    AzureGraphCalendarEventListWithActionType,
):
    """Azure Functions binding for changed Microsoft Graph calendar events."""

    _deserialize = staticmethod(
        deserialize_graph_calendar_events_with_action_type
    )
