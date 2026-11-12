#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Handle OnNewFilesV2 callbacks with OneDrive for Business SDK metadata."""

import logging
from typing import List

import azure.functions as func
import azurefunctions.extensions.connectors.onedriveforbusiness as onedrive

app = func.FunctionApp()


@app.connector_trigger(arg_name="files")
def onedrive_on_new_file_properties_single(
    files: List[onedrive.BlobMetadata],
) -> None:
    """Process a split-on file-property callback as a one-element list."""
    for item in files:
        logging.info(
            "OneDrive file properties received: size '%s', folder '%s'.",
            item.size, item.is_folder,
        )


@app.connector_trigger(arg_name="files")
def onedrive_on_new_file_properties_batch(
    files: List[onedrive.BlobMetadata],
) -> None:
    """Process a source array of file properties with split-on disabled."""
    logging.info("Received metadata for %d OneDrive files.", len(files))
    for item in files:
        logging.info(
            "OneDrive file properties received: size '%s', folder '%s'.",
            item.size, item.is_folder,
        )
