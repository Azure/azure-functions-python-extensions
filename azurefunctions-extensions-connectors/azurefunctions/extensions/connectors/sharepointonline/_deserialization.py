#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Deserialize SharePoint callbacks without losing dynamic column values."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.sharepointonline import DeletedItem, Item
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model


def _parse_sharepoint_payload(data: Datum) -> list[dict[str, Any]]:
    """Normalize callbacks, source arrays, and Poll MANY transport collections."""
    if data.type in ("collection_string", "collection_bytes"):
        return [
            item
            for event in data.python_value
            for item in _parse_sharepoint_payload(Datum(value=event, type="json"))
        ]

    payload: Any = data.value
    if isinstance(payload, (str, bytes, bytearray)):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"Invalid JSON payload: {error}.") from error

    if isinstance(payload, dict) and set(payload) == {"body"}:
        payload = payload["body"]
        if payload is None:
            return []

    if isinstance(payload, dict):
        if "value" in payload and all(
            name == "value" or name.startswith(("@odata.", "odata."))
            for name in payload
        ):
            payload = payload["value"]
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise ValueError("SharePoint batch value must contain a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("SharePoint payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each SharePoint batch item must contain a JSON object.")

    return payload


def deserialize_items(data: Datum) -> list[Item]:
    """Keep dynamic columns as raw JSON in the generated SDK property bag."""
    result = []
    for record in _parse_sharepoint_payload(data):
        if set(record) in ({"dynamicProperties"}, {"dynamic_properties"}):
            properties = next(iter(record.values()))
            if properties is not None and not isinstance(properties, dict):
                raise ValueError(
                    "SharePoint dynamicProperties must be an object or null."
                )
        else:
            properties = record

        result.append(Item(
            dynamic_properties=dict(properties) if properties is not None else None,
        ))

    return result


def deserialize_deleted_items(data: Datum) -> list[DeletedItem]:
    """Read deletion fields using the generated SDK wire-name metadata."""
    return [
        deserialize_model(DeletedItem, record)
        for record in _parse_sharepoint_payload(data)
    ]
