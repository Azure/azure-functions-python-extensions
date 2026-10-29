#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Normalize Azure DevOps polling callbacks into generated SDK item models."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.visualstudioteamservices import (
    BuildResult, GitPullRequest, GitPush, TfvcChangeset, TriggerWorkItemResponse,
)
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model


def _parse_payload(data: Datum) -> list[dict[str, Any]]:
    """Normalize source batches separately from Functions transport batches."""
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
                raise ValueError("Azure DevOps batch value must contain a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("Azure DevOps payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each Azure DevOps batch item must contain a JSON object.")

    return payload


def deserialize_builds(data: Datum) -> list[BuildResult]:
    """Use the _links wire field before a Python-field fallback."""
    return [deserialize_model(BuildResult, item, aliases={"links": "_links"})
            for item in _parse_payload(data)]


def deserialize_pushes(data: Datum) -> list[GitPush]:
    """Build SDK repositories, identities, and ref updates for Git pushes."""
    return [deserialize_model(GitPush, item) for item in _parse_payload(data)]


def deserialize_pull_requests(data: Datum) -> list[GitPullRequest]:
    """Build SDK pull requests and their nested reviewer and option models."""
    return [deserialize_model(GitPullRequest, item) for item in _parse_payload(data)]


def deserialize_changesets(data: Datum) -> list[TfvcChangeset]:
    """Build SDK TFVC changesets with typed author identities."""
    return [deserialize_model(TfvcChangeset, item) for item in _parse_payload(data)]


def deserialize_work_items(data: Datum) -> list[TriggerWorkItemResponse]:
    """Keep the generated fields bag as raw JSON, without a fixed column schema."""
    items = _parse_payload(data)
    if any(item.get("fields") is not None and not isinstance(item["fields"], dict)
           for item in items):
        raise ValueError("Azure DevOps work-item fields must be an object or null.")
    return [deserialize_model(TriggerWorkItemResponse, item) for item in items]
