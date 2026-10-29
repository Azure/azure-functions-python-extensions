#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Normalize Teams polling batches separately from webhook notification bodies."""

from __future__ import annotations

import json
from typing import Any

import azure.connectors.teams as models
from azurefunctions.extensions.base import Datum

from .._deserialization import deserialize_model


def _parse_payload(data: Datum, *, unwrap_value: bool) -> list[dict[str, Any]]:
    """Keep webhook value fields intact while normalizing polling batches."""
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
                raise ValueError("Teams polling batch value must be a JSON array.")
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise ValueError("Teams payload must contain a JSON object or array.")
    if any(not isinstance(item, dict) for item in payload):
        raise ValueError("Each Teams payload item must contain a JSON object.")

    return payload


def deserialize_chat_messages(data: Datum) -> list[models.ChatMessage]:
    """Deserialize polling items while preserving each message's own body."""
    return [
        deserialize_model(models.ChatMessage, record)
        for record in _parse_payload(data, unwrap_value=True)
    ]


def deserialize_membership_changes(data: Datum) -> list[dict[str, Any]]:
    """Keep membership changes as dictionaries, matching the SDK list alias."""
    return [dict(record) for record in _parse_payload(data, unwrap_value=True)]


def deserialize_chat_webhooks(
    data: Datum,
) -> list[models.ChatMessageWebhookResponseSchema]:
    """Preserve notification reference arrays inside their SDK envelopes."""
    result = []
    for record in _parse_payload(data, unwrap_value=False):
        references = record.get("value")
        if references is not None and (
            not isinstance(references, list)
            or any(not isinstance(reference, dict) for reference in references)
        ):
            raise ValueError(
                "Teams chat webhook value must be an array of objects or null."
            )
        result.append(deserialize_model(
            models.ChatMessageWebhookResponseSchema, record,
        ))

    return result


def deserialize_new_messages(
    data: Datum,
) -> list[models.DynamicNewMessageWebhookTriggerResponseSchema]:
    """Retain every field of dynamic new-message notifications."""
    return [
        models.DynamicNewMessageWebhookTriggerResponseSchema(
            additional_properties=dict(record),
        )
        for record in _parse_payload(data, unwrap_value=False)
    ]


def deserialize_mentions(
    data: Datum,
) -> list[models.DynamicAtMentionWebhookTriggerResponseSchema]:
    """Retain every field of dynamic mention notifications."""
    return [
        models.DynamicAtMentionWebhookTriggerResponseSchema(
            additional_properties=dict(record),
        )
        for record in _parse_payload(data, unwrap_value=False)
    ]


def deserialize_keywords(
    data: Datum,
) -> list[models.DynamicKeywordWebhookTriggerResponseSchema]:
    """Retain every field of dynamic keyword notifications."""
    return [
        models.DynamicKeywordWebhookTriggerResponseSchema(
            additional_properties=dict(record),
        )
        for record in _parse_payload(data, unwrap_value=False)
    ]


def deserialize_reactions(
    data: Datum,
) -> list[models.MessageReactionWebhookResponseSchema]:
    """Read reaction notification fields using SDK wire-name metadata."""
    return [
        deserialize_model(models.MessageReactionWebhookResponseSchema, record)
        for record in _parse_payload(data, unwrap_value=False)
    ]


def deserialize_recordings(data: Datum) -> list[models.RecordingWebhookResponseSchema]:
    """Read recording metadata, including OData IDs and nested organizer identities."""
    return [
        deserialize_model(models.RecordingWebhookResponseSchema, record)
        for record in _parse_payload(data, unwrap_value=False)
    ]


def deserialize_transcripts(
    data: Datum,
) -> list[models.TranscriptWebhookResponseSchema]:
    """Read transcript metadata, including OData IDs and nested organizer identities."""
    return [
        deserialize_model(models.TranscriptWebhookResponseSchema, record)
        for record in _parse_payload(data, unwrap_value=False)
    ]
