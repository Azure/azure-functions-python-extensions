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
FOLDER: office365_samples_clientreceivemessage
DESCRIPTION:
    These samples demonstrate how to obtain ClientReceiveMessage objects from
    an Office365 Connector Trigger function app binding.
"""


@app.connector_trigger(arg_name="message")
def office365_trigger_single(message: office365.ClientReceiveMessage):
    """
    Single message processing - splitOn enabled
    Each message triggers an independent function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed a message\n"
        f"Message: {message}"
    )


@app.connector_trigger(arg_name="messages")
def office365_trigger_batch(messages: List[office365.ClientReceiveMessage]):
    """
    Batch message processing - splitOn disabled
    Multiple messages are sent in a single function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed {len(messages)} messages"
    )
    for idx, message in enumerate(messages):
        logging.info(f"Message {idx + 1}: {message}")
