# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365

app = func.FunctionApp()

"""
FOLDER: office365_samples_on_flagged_email
DESCRIPTION:
    These samples demonstrate how to handle the "On Flagged Email" action from
    an Office365 Connector Trigger. The GraphClientReceiveMessage type is the
    rich payload returned when an email is flagged in the mailbox.
"""


@app.connector_trigger(arg_name="message")
def office365_on_flagged_email_single(
    message: List[office365.GraphClientReceiveMessage]
):
    """
    Single message processing - splitOn enabled
    Each flagged email triggers an independent function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed a message\n"
        f"Message: {message[0]}"
    )


@app.connector_trigger(arg_name="messages")
def office365_on_flagged_email_batch(
    messages: List[office365.GraphClientReceiveMessage]
):
    """
    Batch message processing - splitOn disabled
    Multiple flagged emails are sent in a single function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed "
        f"{len(messages)} messages"
    )
    for idx, message in enumerate(messages):
        logging.info(f"Message {idx + 1}: {message}")
