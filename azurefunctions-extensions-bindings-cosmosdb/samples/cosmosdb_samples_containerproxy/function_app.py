# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging

import azure.functions as func
import azurefunctions.extensions.bindings.cosmosdb as cosmos

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

"""
FOLDER: cosmosdb_samples_containerproxy
DESCRIPTION:
    These samples demonstrate how to obtain a ContainerProxy from a Cosmos DB Input function app binding.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    1) CosmosDBConnection - the connection string to your Cosmos DB instance

    Set database_name and container_name to the database name the and container name you want to use
    as inputs to the function (required).
"""


@app.route(route="container")
@app.cosmos_db_input(arg_name="container",
                     connection="CosmosDBConnection",
                     database_name="db_name",
                     container_name="container_name")
def get_docs(req: func.HttpRequest, container: cosmos.ContainerProxy):
    docs = container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True)
    for d in docs:
        logging.info(f"Found document: {d}")

    return "ok"
