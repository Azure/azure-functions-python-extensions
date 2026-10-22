#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle Salesforce record callbacks using generated SDK item property bags."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.salesforce as salesforce

app = func.FunctionApp()


@app.connector_trigger(arg_name="records")
def salesforce_new_record_single(records: List[salesforce.Item]) -> None:
    """Handle a GetOnNewItems split-on callback as a list of SDK items."""
    logging.info("Received %d new Salesforce records.", len(records))
    for record in records:
        logging.info("Salesforce record field count: %d.",
                     len(record.dynamic_properties or {}))


@app.connector_trigger(arg_name="records")
def salesforce_new_record_batch(records: List[salesforce.Item]) -> None:
    """Handle GetOnNewItems with split-on disabled."""
    logging.info("Received a batch of %d new Salesforce records.", len(records))
    for record in records:
        logging.info("Salesforce record field count: %d.",
                     len(record.dynamic_properties or {}))


@app.connector_trigger(arg_name="records")
def salesforce_updated_record(records: List[salesforce.Item]) -> None:
    """Handle GetOnUpdatedItems without assuming a fixed object schema."""
    logging.info("Received %d updated Salesforce records.", len(records))
    for record in records:
        logging.info("Salesforce record field count: %d.",
                     len(record.dynamic_properties or {}))
