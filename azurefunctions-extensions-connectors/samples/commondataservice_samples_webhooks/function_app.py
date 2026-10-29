#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle dynamic row and action callbacks from the commondataservice connector."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.commondataservice as cds

app = func.FunctionApp()


@app.connector_trigger(arg_name="notifications")
def dataverse_row_changed(notifications: List[cds.RowChangeNotification]) -> None:
    """Handle SubscribeWebhookTrigger using SDK ObjectEntity records."""
    for notification in notifications:
        logging.info(
            "Received a Dataverse row notification with %d fields.",
            len(notification.additional_properties),
        )


@app.connector_trigger(arg_name="notifications")
def dataverse_action_performed(
    notifications: List[cds.ActionEventNotification],
) -> None:
    """Handle BusinessEventsTrigger without imposing a fixed action schema."""
    for notification in notifications:
        logging.info(
            "Received a Dataverse action notification with %d fields.",
            len(notification.additional_properties),
        )
