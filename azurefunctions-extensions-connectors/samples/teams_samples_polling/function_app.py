#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle Teams channel-message and membership polling callbacks."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.teams as teams

app = func.FunctionApp()


@app.connector_trigger(arg_name="messages")
def teams_channel_message_single(messages: List[teams.ChatMessage]) -> None:
    """Handle a split-on OnNewChannelMessage callback."""
    logging.info("Received %d Teams channel messages.", len(messages))


@app.connector_trigger(arg_name="messages")
def teams_channel_message_batch(messages: List[teams.ChatMessage]) -> None:
    """Handle OnNewChannelMessageMentioningMe with split-on disabled."""
    logging.info("Received %d Teams mention messages.", len(messages))


@app.connector_trigger(arg_name="members")
def teams_member_added(members: teams.OnGroupMemberChangeResponse) -> None:
    """Handle OnGroupMembershipAdd as the SDK's list of member dictionaries."""
    logging.info("Received %d Teams member additions.", len(members))


@app.connector_trigger(arg_name="members")
def teams_member_removed(members: teams.OnGroupMemberChangeResponse) -> None:
    """Handle OnGroupMembershipRemoval without guessing custom member fields."""
    logging.info("Received %d Teams member removals.", len(members))
