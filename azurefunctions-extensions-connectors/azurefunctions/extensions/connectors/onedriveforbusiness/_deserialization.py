#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Deserialize file metadata without treating binary content as a model."""

from __future__ import annotations

import json
from typing import Any

from azure.connectors.onedriveforbusiness import BlobMetadata
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model

_BLOB_METADATA_ALIASES = {
    "id": "Id",
    "name": "Name",
    "name_no_ext": "NameNoExt",
    "display_name": "DisplayName",
    "path": "Path",
    "last_modified": "LastModified",
    "size": "Size",
    "media_type": "MediaType",
    "is_folder": "IsFolder",
    "e_tag": "ETag",
    "file_locator": "FileLocator",
    "last_modified_by": "LastModifiedBy",
}


def _parse_metadata_payload(data: Datum) -> list[dict[str, Any]]:
    """Normalize direct metadata, source arrays, and Poll MANY collections."""
    if data.type in ("collection_string", "collection_bytes"):
        return [
            item
            for event in data.python_value
            for item in _parse_metadata_payload(Datum(value=event, type="json"))
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
            name in ("value", "nextLink", "next_link")
            or name.startswith(("@odata.", "odata."))
            for name in payload
        ):
            payload = payload["value"]
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise ValueError("OneDrive metadata batch value must be a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("OneDrive metadata must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each OneDrive metadata batch item must be a JSON object.")
    if any("$content" in item or "$content-type" in item for item in payload):
        raise ValueError("OneDrive file content cannot be bound to BlobMetadata.")

    return payload


def deserialize_blob_metadata(data: Datum) -> list[BlobMetadata]:
    """Read metadata wire names, including SDK versions without field metadata."""
    return [
        deserialize_model(BlobMetadata, record, aliases=_BLOB_METADATA_ALIASES)
        for record in _parse_metadata_payload(data)
    ]
