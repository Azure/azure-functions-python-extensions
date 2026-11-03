#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle GetOnDeletedItems callbacks with generated SDK deletion metadata."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.sharepointonline as sharepointonline

app = func.FunctionApp()


@app.connector_trigger(arg_name="items")
def sharepoint_on_deleted_item_single(
    items: List[sharepointonline.DeletedItem],
) -> None:
    """Process a split-on deletion callback as a one-element list."""
    for item in items:
        logging.info(
            "SharePoint item deleted: ID '%s', folder '%s'.",
            item.id, item.is_folder,
        )


@app.connector_trigger(arg_name="items")
def sharepoint_on_deleted_item_batch(
    items: List[sharepointonline.DeletedItem],
) -> None:
    """Process a source batch of deletion metadata with split-on disabled."""
    logging.info("Received %d SharePoint deletions.", len(items))
    for item in items:
        logging.info(
            "SharePoint item deleted: ID '%s', folder '%s'.",
            item.id, item.is_folder,
        )
