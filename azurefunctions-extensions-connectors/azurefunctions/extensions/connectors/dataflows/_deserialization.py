#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Normalize Dataflows refresh records without inventing a source collection."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.dataflows import RefreshModel
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model


def _parse_payload(data: Datum) -> list[dict[str, Any]]:
    """Read single refresh callbacks and optional transport-level aggregates."""
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
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Dataflows payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each Dataflows transport item must contain a JSON object.")
    if any("value" in item and all(
        name == "value" or name.startswith(("@odata.", "odata.")) for name in item
    ) for item in payload):
        raise ValueError(
            "Dataflows OnRefreshComplete returns a refresh record, "
            "not a value collection."
        )

    return payload


def deserialize_refreshes(data: Datum) -> list[RefreshModel]:
    """Map the six nullable SDK string fields without changing their values."""
    return [deserialize_model(RefreshModel, item) for item in _parse_payload(data)]
