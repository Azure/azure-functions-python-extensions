#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind changed calendar events using the generated SDK item type."""

import azure.connectors.office365 as office365

from .._sdk_type import ConnectorSdkType
from ._deserialization import (
    deserialize_graph_calendar_events_with_action_type,
)


class GraphCalendarEventClientWithActionType(
    ConnectorSdkType[list[office365.GraphCalendarEventClientWithActionType]],
    office365.GraphCalendarEventClientWithActionType,
):
    """Bind calendar changes as a list of SDK items, including split-on events."""

    _deserialize = staticmethod(
        deserialize_graph_calendar_events_with_action_type
    )
