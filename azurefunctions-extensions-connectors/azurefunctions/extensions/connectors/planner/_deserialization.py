#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Deserialize Planner task callbacks without changing the SDK model contract."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.planner import GetTaskResponseV2
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model


def _parse_payload(data: Datum) -> list[dict[str, Any]]:
    """Normalize split records, polling batches, and transport collections."""
    if data.type in ("collection_string", "collection_bytes"):
        return [
            item
            for event in data.python_value
            for item in _parse_payload(Datum(value=event, type="json"))
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
                raise ValueError("Planner batch value must contain a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("Planner payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each Planner batch item must contain a JSON object.")

    return payload


def _deserialize_assignments(value: Any) -> list[dict[str, Any]] | None:
    """Keep the connector assignment array distinct from native Graph objects."""
    if value is not None and (
        not isinstance(value, list)
        or any(not isinstance(item, dict) for item in value)
    ):
        raise ValueError("Planner assignments must be an array of objects or null.")
    return value


def deserialize_tasks(data: Datum) -> list[GetTaskResponseV2]:
    """Read SDK task fields, preferring the connector's _assignments wire name."""
    return [
        deserialize_model(
            GetTaskResponseV2, record,
            aliases={"assignments": "_assignments"},
            converters={"assignments": _deserialize_assignments},
        )
        for record in _parse_payload(data)
    ]
