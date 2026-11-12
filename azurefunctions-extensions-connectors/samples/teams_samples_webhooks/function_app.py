#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle the seven Teams webhook notification payload families."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.teams as teams

app = func.FunctionApp()


@app.connector_trigger(arg_name="notifications")
def teams_chat_message(
    notifications: List[teams.ChatMessageWebhookResponseSchema],
) -> None:
    """Handle WebhookChatMessageTrigger without flattening its value envelope."""
    for notification in notifications:
        logging.info(
            "Received %d chat message references.", len(notification.value or []),
        )


@app.connector_trigger(arg_name="notifications")
def teams_new_message(
    notifications: List[teams.DynamicNewMessageWebhookTriggerResponseSchema],
) -> None:
    """Handle WebhookNewMessageTrigger with raw JSON in additional_properties."""
    for notification in notifications:
        logging.info(
            "Received a Teams new-message notification with %d fields.",
            len(notification.additional_properties),
        )


@app.connector_trigger(arg_name="notifications")
def teams_at_mention(
    notifications: List[teams.DynamicAtMentionWebhookTriggerResponseSchema],
) -> None:
    """Handle WebhookAtMentionTrigger with its dynamic field bag intact."""
    for notification in notifications:
        logging.info(
            "Received a Teams mention notification with %d fields.",
            len(notification.additional_properties),
        )


@app.connector_trigger(arg_name="notifications")
def teams_keyword(
    notifications: List[teams.DynamicKeywordWebhookTriggerResponseSchema],
) -> None:
    """Handle WebhookKeywordTrigger without imposing a fixed message schema."""
    for notification in notifications:
        logging.info(
            "Received a Teams keyword notification with %d fields.",
            len(notification.additional_properties),
        )


@app.connector_trigger(arg_name="notifications")
def teams_reaction(
    notifications: List[teams.MessageReactionWebhookResponseSchema],
) -> None:
    """Handle WebhookMessageReactionTrigger as SDK notification metadata."""
    logging.info("Received %d Teams reaction notifications.", len(notifications))


@app.connector_trigger(arg_name="notifications")
def teams_recording(
    notifications: List[teams.RecordingWebhookResponseSchema],
) -> None:
    """Handle RecordingTrigger metadata without downloading recording bytes."""
    logging.info("Received %d recording notifications.", len(notifications))


@app.connector_trigger(arg_name="notifications")
def teams_transcript(
    notifications: List[teams.TranscriptWebhookResponseSchema],
) -> None:
    """Handle TranscriptTrigger metadata without downloading transcript text."""
    logging.info("Received %d transcript notifications.", len(notifications))
