#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Deserialize Office 365 trigger payloads into Azure Connector SDK models."""

from __future__ import annotations

from typing import Any

from azure.connectors.office365 import (
    ClientReceiveMessage,
    GraphCalendarEventClientReceive,
    GraphCalendarEventClientWithActionType,
    GraphCalendarEventListWithActionType,
    GraphClientReceiveMessage,
)
from azurefunctions.extensions.base import Datum
from .._deserialization import deserialize_model, parse_payload

_CLIENT_MESSAGE_ALIASES = {
    "to": "toRecipients",
    "cc": "ccRecipients",
    "bcc": "bccRecipients",
    "has_attachment": "hasAttachments",
    "date_time_received": "receivedDateTime",
}


def _deserialize_importance(value: Any) -> int | None:
    """Convert the legacy email importance wire value to its SDK integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return {"low": 0, "normal": 1, "high": 2}.get(value.lower())
    return None


def deserialize_client_receive_messages(
    data: Datum,
) -> list[ClientReceiveMessage]:
    """Deserialize legacy Office 365 email trigger messages."""
    return [
        deserialize_model(
            ClientReceiveMessage,
            item,
            aliases=_CLIENT_MESSAGE_ALIASES,
            converters={"importance": _deserialize_importance},
        )
        for item in parse_payload(data)
    ]


def deserialize_graph_client_receive_messages(
    data: Datum,
) -> list[GraphClientReceiveMessage]:
    """Deserialize Microsoft Graph email trigger messages."""
    return [
        deserialize_model(GraphClientReceiveMessage, item)
        for item in parse_payload(data)
    ]


def deserialize_graph_calendar_events(
    data: Datum,
) -> list[GraphCalendarEventClientReceive]:
    """Deserialize Microsoft Graph calendar event trigger items."""
    return [
        deserialize_model(GraphCalendarEventClientReceive, item)
        for item in parse_payload(data)
    ]


def deserialize_graph_calendar_events_with_action_type(
    data: Datum,
) -> GraphCalendarEventListWithActionType:
    """Deserialize changed calendar events into their generated list wrapper."""
    events = [
        deserialize_model(GraphCalendarEventClientWithActionType, item)
        for item in parse_payload(data)
    ]
    return GraphCalendarEventListWithActionType(value=events)
