#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Preserve dynamic Dataverse records without treating schema metadata as data."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.commondataservice import Item, ObjectEntity
from azurefunctions.extensions.base import Datum


def _parse_payload(data: Datum, *, unwrap_value: bool) -> list[dict[str, Any]]:
    """Extract polling batches, but keep webhook value fields as record data."""
    if data.type in ("collection_string", "collection_bytes"):
        return [
            item
            for event in data.python_value
            for item in _parse_payload(
                Datum(value=event, type="json"), unwrap_value=unwrap_value,
            )
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
        if unwrap_value and "value" in payload and all(
            name == "value" or name.startswith(("@odata.", "odata."))
            for name in payload
        ):
            payload = payload["value"]
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise ValueError("CDS polling batch value must contain a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("CDS payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each CDS payload item must contain a JSON object.")

    return payload


def deserialize_items(data: Datum) -> list[Item]:
    """Store legacy polling columns in the generated SDK dynamic property bag."""
    result = []
    for record in _parse_payload(data, unwrap_value=True):
        if set(record) in ({"dynamicProperties"}, {"dynamic_properties"}):
            properties = next(iter(record.values()))
            if properties is not None and not isinstance(properties, dict):
                raise ValueError("CDS dynamicProperties must be an object or null.")
        else:
            properties = record

        result.append(Item(
            dynamic_properties=dict(properties) if properties is not None else None,
        ))

    return result


def deserialize_notifications(data: Datum) -> list[ObjectEntity]:
    """Keep complete webhook records in SDK ObjectEntity additional_properties."""
    return [
        ObjectEntity(additional_properties=dict(record))
        for record in _parse_payload(data, unwrap_value=False)
    ]
