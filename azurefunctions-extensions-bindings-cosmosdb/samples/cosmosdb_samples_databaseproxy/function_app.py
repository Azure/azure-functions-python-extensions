import logging

import azure.functions as func
import azurefunctions.extensions.bindings.cosmosdb as cosmos

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


"""
FOLDER: cosmosdb_samples_databaseproxy
DESCRIPTION:
    These samples demonstrate how to obtain a DatabaseProxy from a Cosmos DB Input function app binding.
USAGE:
    Set the environment variables with your own values before running the
    sample:
    1) CosmosDBConnection - the connection string to your Cosmos DB instance

    Set database_name to the database you want to use as an input to the function (required).
"""


@app.route(route="database")
@app.cosmos_db_input(arg_name="container",
                     connection="CosmosDBConnection",
                     database_name="db_name",
                     container_name=None)
def get_docs(req: func.HttpRequest, database: cosmos.DatabaseProxy):
    containers = database.list_containers()
    for c in containers:
        logging.info(f"Found container with ID: {c.get('id')}")

    return "ok"
