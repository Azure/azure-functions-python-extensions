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
FOLDER: office365_samples_on_calendar_event_created
DESCRIPTION:
    These samples demonstrate how to handle calendar event actions from an
    Office365 Connector Trigger. The GraphCalendarEventClientReceive type is
    the rich payload returned for the following actions:
    - When a new event is created
    - When an event is modified
    - When an upcoming event is starting soon
"""


@app.connector_trigger(arg_name="event")
def office365_on_calendar_event_created_single(
    event: List[office365.GraphCalendarEventClientReceive]
):
    """
    Single event processing - splitOn enabled
    Each calendar event triggers an independent function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger processed a calendar event\n"
        f"Event: {event[0]}"
    )


@app.connector_trigger(arg_name="events")
def office365_on_calendar_event_created_batch(
    events: List[office365.GraphCalendarEventClientReceive]
):
    """
    Batch event processing - splitOn disabled
    Multiple calendar events are sent in a single function invocation.
    """
    logging.info(
        f"Python Office365 Connector trigger processed "
        f"{len(events)} calendar events"
    )
    for idx, event in enumerate(events):
        logging.info(f"Event {idx + 1}: {event}")
