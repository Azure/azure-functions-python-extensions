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
FOLDER: office365_samples_on_calendar_event
DESCRIPTION:
    These samples demonstrate how to handle the "When an event is added,
    updated or deleted" action from an Office365 Connector Trigger. The
    GraphCalendarEventListWithActionType type is the rich payload returned
    when a calendar event is added, updated, or deleted.
"""


@app.connector_trigger(arg_name="event")
def office365_on_calendar_event_single(
    event: List[office365.GraphCalendarEventListWithActionType]
):
    """
    Single event processing - splitOn enabled
    Each calendar event change triggers an independent function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed a "
        f"calendar event\n"
        f"Event: {event[0]}"
    )


@app.connector_trigger(arg_name="events")
def office365_on_calendar_event_batch(
    events: List[office365.GraphCalendarEventListWithActionType]
):
    """
    Batch event processing - splitOn disabled
    Multiple calendar event changes are sent in a single function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger function processed "
        f"{len(events)} calendar events"
    )
    for idx, event in enumerate(events):
        logging.info(f"Event {idx + 1}: {event}")
