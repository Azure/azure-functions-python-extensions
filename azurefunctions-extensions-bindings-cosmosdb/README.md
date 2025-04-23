# Azure Functions Extensions Bindings Cosmos DB library for Python
This library allows Cosmos DB Input bindings in Python Function Apps to recognize and bind to client types from the
Azure Cosmos DB SDK.

Cosmos DB client types can be generated from:

* Cosmos DB Input

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-cosmosdb)
[Package (PyPi)](https://pypi.org/project/azurefunctions-extensions-bindings-cosmosdb/)
| API reference documentation
| Product documentation
| [Samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-cosmosdb/samples)


## Getting started

### Prerequisites
* Python 3.9 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an
[Azure storage account](https://docs.microsoft.com/azure/storage/common/storage-account-overview) to use this package.

### Install the package
Install the Azure Functions Extensions Bindings Cosmos DB library for Python with pip:

```bash
pip install azurefunctions-extensions-bindings-cosmosdb
```

### Create a storage account
If you wish to create a new storage account, you can use the
[Azure Portal](https://docs.microsoft.com/azure/storage/common/storage-quickstart-create-account?tabs=azure-portal),
[Azure PowerShell](https://docs.microsoft.com/azure/storage/common/storage-quickstart-create-account?tabs=azure-powershell),
or [Azure CLI](https://docs.microsoft.com/azure/storage/common/storage-quickstart-create-account?tabs=azure-cli):

```bash
# Create a new resource group to hold the storage account -
# if using an existing resource group, skip this step
az group create --name my-resource-group --location westus2

# Create the storage account
az storage account create -n my-storage-account-name -g my-resource-group
```

### Bind to the SDK-type
The Azure Functions Extensions Bindings Cosmos DB library for Python allows you to create a function app with
Cosmos DB Input and define the type as a CosmosClient, DatabaseProxy, or ContainerProxy. Instead of receiving
an InputStream, when the function is executed, the type returned will be the defined SDK-type and have all of the
properties and methods available as seen in the Azure Storage Cosmos DB library for Python.


```python
import logging
import azure.functions as func
import azurefunctions.extensions.bindings.cosmosdb as cosmos

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="cosmos")
@app.cosmos_db_input(arg_name="container",
                     connection="CosmosDBConnection",
                     database_name="db_name",
                     container_name="container_name")
def get_docs(req: func.HttpRequest, client: cosmos.CosmosClient):
    databases = client.list_databases()
    for db in databases:
        logging.info(f"Found database with ID: {db.get('id')}")

    return "ok"
```

## Troubleshooting
### General
The SDK-types raise exceptions defined in [Azure Core](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md).

This list can be used for reference to catch thrown exceptions. To get the specific error code of the exception, use the `error_code` attribute, i.e, `exception.error_code`.

## Next steps

### More sample code

Get started with our [Cosmos DB samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-cosmosdb/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with Cosmos DB:

* [cosmosdb_samples_cosmosclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-binding-cosmosdb/samples/cosmosdb_samples_cosmosclient)  - Examples for using the CosmosClient type:
    * From CosmosDBInput

* [cosmosdb_samples_databaseproxy](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-cosmosdb/samples/cosmosdb_samples_databaseproxy) - Examples for using the DatabaseProxy type:
    * From CosmosDBInput

* [cosmosdb_samples_containerclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-cosmosdb/samples/cosmosdb_samples_containerproxy) - Examples for using the ContainerProxy type:
    * From CosmosDBInput

### Additional documentation
For more information on the Azure Cosmos DB SDK, see the [Azure Cosmos DB documentation](https://learn.microsoft.com/en-us/azure/cosmos-db/) on learn.microsoft.com
and the [Azure Cosmos DB README](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/cosmos/azure-cosmos).

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.