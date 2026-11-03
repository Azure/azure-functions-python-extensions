#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle GetOnNewItems callbacks with generated SharePoint SDK items."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.sharepointonline as sharepointonline

app = func.FunctionApp()


@app.connector_trigger(arg_name="items")
def sharepoint_on_new_item_single(items: List[sharepointonline.Item]) -> None:
    """Process a split-on item callback, returned as a one-element list."""
    for item in items:
        properties = item.dynamic_properties or {}
        logging.info("SharePoint item received: ID '%s'.", properties.get("ID"))


@app.connector_trigger(arg_name="items")
def sharepoint_on_new_item_batch(items: List[sharepointonline.Item]) -> None:
    """Process a source batch with split-on disabled."""
    logging.info("Received %d SharePoint items.", len(items))
    for item in items:
        properties = item.dynamic_properties or {}
        logging.info("SharePoint item received: ID '%s'.", properties.get("ID"))
