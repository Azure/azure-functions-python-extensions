#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle deprecated CDS V2 polling callbacks for existing trigger registrations."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.commondataservice as cds

app = func.FunctionApp()


@app.connector_trigger(arg_name="items")
def cds_legacy_row_added(items: List[cds.Item]) -> None:
    """Handle an existing GetOnNewItems_V2 trigger registration."""
    for item in items:
        logging.info("Received a legacy CDS row with %d fields.",
                     len(item.dynamic_properties or {}))


@app.connector_trigger(arg_name="items")
def cds_legacy_row_updated(items: List[cds.Item]) -> None:
    """Handle an existing GetOnUpdatedItems_V2 trigger registration."""
    for item in items:
        logging.info("Received a legacy CDS row update with %d fields.",
                     len(item.dynamic_properties or {}))


@app.connector_trigger(arg_name="items")
def cds_legacy_row_deleted(items: List[cds.Item]) -> None:
    """Handle an existing GetOnDeletedItems_V2 trigger registration."""
    for item in items:
        logging.info("Received a legacy CDS row deletion with %d fields.",
                     len(item.dynamic_properties or {}))
