import logging

import azure.functions as func
import azurefunctions.extensions.bindings.cosmos as cosmos

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


"""
FOLDER: cosmos_samples_cosmosclient
DESCRIPTION:
    These samples demonstrate how to obtain a CosmosClient from a Cosmos Input function app binding.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    1) AzureWebJobsStorage - the connection string to your storage account

    Set database_name and container_name to the path to the container you want to use
    as inputs to the function (required).
"""


@app.route(route="cosmos")
@app.cosmos_db_input(arg_name="container",
                     connection="AzureWebJobsStorage",
                     database_name="db_name",
                     container_name="container_name")
def get_docs(req: func.HttpRequest, client: cosmos.CosmosClient):
    databases = client.list_databases()
    for db in databases:
        logging.info(f"Found database with ID: {db.get('id')}")

    return "ok"
