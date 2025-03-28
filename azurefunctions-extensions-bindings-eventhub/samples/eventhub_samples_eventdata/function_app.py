# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import azure.functions as func
import azurefunctions.extensions.bindings.eventhub as eh

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

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
    arg_name="eh_data", event_hub_name="EVENTHUB_NAME", connection="AzureWebJobsStorage"
) 
def eventhub_trigger(eh_data: eh.EventData):
    logging.info(
        "Python EventHub trigger processed an event %s",
        eh_data.body_as_str()
    )
    