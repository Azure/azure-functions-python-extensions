#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle Dataflows refresh completion using the generated SDK refresh model."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.dataflows as dataflows

app = func.FunctionApp()


@app.connector_trigger(arg_name="refreshes")
def dataflows_refresh_completed(refreshes: List[dataflows.RefreshModel]) -> None:
    """Handle OnRefreshComplete records without logging names or identifiers."""
    logging.info("Received %d Dataflows refresh completions.", len(refreshes))
    logging.info("Failed Dataflows refresh count: %d.",
                 sum(refresh.status == "Failed" for refresh in refreshes))
