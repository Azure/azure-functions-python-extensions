# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging

import azure.functions as func
import azurefunctions.extensions.bindings.servicebus as servicebus

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

"""
FOLDER: servicebus_samples
DESCRIPTION:
    These samples demonstrate how to obtain a ServiceBusReceivedMessage
    from a ServiceBus Trigger.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    For running the ServiceBus queue trigger function:
        1) QUEUE_NAME - the name of the ServiceBus queue
        2) SERVICEBUS_CONNECTION - the connection string for the ServiceBus entity
    For running the ServiceBus topic trigger function:
        1) TOPIC_NAME - the name of the ServiceBus topic
        2) SERVICEBUS_CONNECTION - the connection string for the ServiceBus entity
        3) SUBSCRIPTION_NAME - the name of the Subscription
"""


@app.service_bus_queue_trigger(arg_name="receivedmessage",
                               queue_name="QUEUE_NAME",
                               connection="SERVICEBUS_CONNECTION",
                               auto_complete_messages=False)
def servicebus_queue_trigger(receivedmessage: servicebus.ServiceBusReceivedMessage, message: servicebus.ServiceBusMessageActions):
    logging.info(f"Python ServiceBus queue trigger processed message. Message: {receivedmessage}")
    message.complete(receivedmessage)
    logging.info("Completed message.")
