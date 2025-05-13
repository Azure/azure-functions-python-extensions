# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.bindings.eventhub as eh

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

"""
FOLDER: eventhub_samples_eventdata
DESCRIPTION:
    These samples demonstrate how to obtain EventData from an EventHub Trigger.
USAGE:
    There are different ways to connect to an EventHub via the connection property and
    envionrment variables specifiied in local.settings.json
    
    The connection property can be:
    - The name of an application setting containing a connection string
    - The name of a shared prefix for multiple application settings, together defining an identity-based connection

    For more information, see:
    https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-event-hubs-trigger?tabs=python-v2%2Cisolated-process%2Cnodejs-v4%2Cfunctionsv2%2Cextensionv5&pivots=programming-language-python
"""


@app.event_hub_message_trigger(
    arg_name="event", event_hub_name="EVENTHUB_NAME", connection="EventHubConnection"
)
def eventhub_trigger(event: eh.EventData):
    logging.info(
        "Python EventHub trigger processed an event %s",
        event.body_as_str()
    )


@app.event_hub_message_trigger(
    arg_name="events", event_hub_name="EVENTHUB_NAME", connection="EventHubConnection", cardinality="many"
)
def eventhub_trigger(events: List[eh.EventData]):
    for event in events:
        logging.info(
            "Python EventHub trigger processed an event %s",
            event.body_as_str()
        )
