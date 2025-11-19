# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import azure.functions as func
import azurefunctions.extensions.bindings.servicebus as servicebus

from azure.identity import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

import datetime
import logging
import os

"""
FOLDER: servicebus_samples_exponential_backoff
DESCRIPTION:
    These samples demonstrate how to schedule messages with exponential backoff
    retries using ServiceBus Trigger and ServiceBusMessageActions.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    For running the ServiceBus queue trigger function:
        1) QUEUE_NAME - the name of the ServiceBus queue
        2) SERVICEBUS_CONNECTION - the connection string for the ServiceBus entity
"""

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

MAX_RETRIES = 3

@app.service_bus_queue_trigger(arg_name="received_message",
                               queue_name="mysbqueue",
                               connection="SERVICEBUS_CONNECTION",
                               auto_complete_messages=False)
async def servicebus_queue_trigger(received_message: servicebus.ServiceBusReceivedMessage, message_actions: servicebus.ServiceBusMessageActions):
    logging.info(f"Python ServiceBus queue trigger processed message.")

    application_properties = received_message.application_properties or {}

    logging.info(f"Received message: {received_message}. Message application properties: {application_properties}")

    # Read retry count
    current_retry_count = int(application_properties.get(b"retry_count", 0))
    logging.info(f"Current retry count: {current_retry_count}, Max: {MAX_RETRIES}")

    # If max retries exceeded -> dead-letter
    if current_retry_count >= MAX_RETRIES:
        logging.warning("Max retries exceeded. Dead-lettering message.")
        message_actions.deadletter(received_message, deadletter_reason="MaxRetryExceeded")
        return

    try:
        # Complete original message
        logging.info(f"Completing original message {received_message}.")
        message_actions.complete(received_message)
        logging.info("Original message completed successfully")

        # ----- Service Bus Client Setup -----
        # Determine Service Bus client: connection string or Managed Identity
        conn = os.getenv("SERVICEBUS_CONNECTION")
        fqns = os.getenv("SERVICEBUS_CONNECTION__fullyQualifiedNamespace")

        # ----- Create client -----
        if conn and "SharedAccessKey" in conn:
            logging.info("Using ServiceBus connection string with shared access key")
            sb_client = ServiceBusClient.from_connection_string(conn)
        elif fqns:
            logging.info(f"Using Managed Identity with namespace: {fqns}")
            sb_client = ServiceBusClient(
                fully_qualified_namespace=fqns,
                credential=DefaultAzureCredential()
            )
        else:
            raise RuntimeError(
                "Neither SERVICEBUS_CONNECTION nor SERVICEBUS_CONNECTION__fullyQualifiedNamespace is configured"
            )

        # Sender for the queue
        sender = sb_client.get_queue_sender(queue_name="mysbqueue")

        async with sb_client, sender:
            # NEW retry count
            new_retry_count = current_retry_count + 1

            # Schedule the new message for +10 seconds
            schedule_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=10)

            new_message = ServiceBusMessage(
                body=str(received_message),
                application_properties={
                    **application_properties,
                    "retry_count": new_retry_count,
                    "original_message_id": received_message.message_id,
                    "scheduled_at": datetime.datetime.utcnow().isoformat(),
                    "original_enqueue_time": received_message.enqueued_time_utc.isoformat() if received_message.enqueued_time_utc else None
                },
                message_id=received_message.message_id,
                session_id=received_message.session_id,
                content_type=received_message.content_type,
                correlation_id=received_message.correlation_id,
                subject=received_message.subject
            )

            # Send the new message
            sequence_number = await sender.schedule_messages(
                new_message,
                schedule_time
            )

            logging.info(f"Message scheduled with sequence number: {sequence_number}")
            logging.info(f"Retry count incremented to: {new_retry_count}")


    except Exception as e:
        logging.exception("Error processing message. Abandoning message.")
        message_actions.abandon(received_message)
        raise


