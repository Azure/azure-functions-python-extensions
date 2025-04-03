# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging

import azure.functions as func
import azurefunctions.extensions.bindings.blob as blob

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

"""
FOLDER: blob_samples_blobclient
DESCRIPTION:
    These samples demonstrate how to obtain a BlobClient from a Blob Trigger
    or Blob Input function app binding.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    1) AzureWebJobsStorage - the connection string to your storage account

    Set PATH/TO/BLOB to the path to the blob you want to trigger or serve as
    input to the function.
"""


@app.blob_trigger(
    arg_name="client", path="PATH/TO/BLOB", connection="AzureWebJobsStorage"
)
def blob_trigger(client: blob.BlobClient):
    logging.info(
        f"Python blob trigger function processed blob \n"
        f"Properties: {client.get_blob_properties()}\n"
        f"Blob content head: {client.download_blob().read(size=1)}"
    )


@app.route(route="file")
@app.blob_input(
    arg_name="client", path="PATH/TO/BLOB", connection="AzureWebJobsStorage"
)
def blob_input(req: func.HttpRequest, client: blob.BlobClient):
    logging.info(
        f"Python blob input function processed blob \n"
        f"Properties: {client.get_blob_properties()}\n"
        f"Blob content head: {client.download_blob().read(size=1)}"
    )
    return "ok"
