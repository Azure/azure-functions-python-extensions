# Azure Functions Extensions Bindings Blob library for Python
This library allows Blob Trigger and Blob Input bindings in Python Function Apps to recognize and bind to client types from the
Azure Storage Blob sdk.

Blob client types can be generated from:

* Blob Triggers
* Blob Input

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob)
[Package (PyPi)](https://pypi.org/project/azurefunctions-extensions-bindings-blob/)
| API reference documentation
| Product documentation
| [Samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples)


## Getting started

### Prerequisites
* Python 3.9 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an
[Azure storage account](https://docs.microsoft.com/azure/storage/common/storage-account-overview) to use this package.

### Install the package
Install the Azure Functions Extensions Bindings Blob library for Python with pip:

```bash
pip install azurefunctions-extensions-bindings-blob
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
The Azure Functions Extensions Bindings Blob library for Python allows you to create a function app with a Blob Trigger or
Blob Input and define the type as a BlobClient, ContainerClient, or StorageStreamDownloader. Instead of receiving
an InputStream, when the function is executed, the type returned will be the defined SDK-type and have all of the
properties and methods available as seen in the Azure Storage Blob library for Python.


```python
import logging
import azure.functions as func
import azurefunctions.extensions.bindings.blob as blob

@app.blob_trigger(arg_name="client",
                  path="PATH/TO/BLOB",
                  connection="AzureWebJobsStorage")
def blob_trigger(client: blob.BlobClient):
    logging.info(f"Python blob trigger function processed blob \n"
                 f"Properties: {client.get_blob_properties()}\n"
                 f"Blob content head: {client.download_blob(encoding="utf-8").read(size=1)}")


@app.route(route="file")
@app.blob_input(arg_name="client",
                path="PATH/TO/BLOB",
                connection="AzureWebJobsStorage")
def blob_input(req: func.HttpRequest, client: blob.BlobClient):
    logging.info(f"Python blob input function processed blob \n"
                 f"Properties: {client.get_blob_properties()}\n"
                 f"Blob content head: {client.download_blob(encoding="utf-8").read(size=1)}")
```

## Troubleshooting
### General
The SDK-types raise exceptions defined in [Azure Core](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md).

This list can be used for reference to catch thrown exceptions. To get the specific error code of the exception, use the `error_code` attribute, i.e, `exception.error_code`.

## Next steps

### More sample code

Get started with our [Blob samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with Storage Blobs:

* [blob_samples_blobclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_blobclient)  - Examples for using the BlobClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_containerclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_containerclient) - Examples for using the ContainerClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_storagestreamdownloader](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_storagestreamdownloader) - Examples for using the StorageStreamDownloader type:
    * From BlobTrigger
    * From BlobInput

### Additional documentation
For more information on the Azure Storage Blob SDK, see the [Azure Blob storage documentation](https://docs.microsoft.com/azure/storage/blobs/) on docs.microsoft.com
and the [Azure Storage Blobs README](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob).

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.