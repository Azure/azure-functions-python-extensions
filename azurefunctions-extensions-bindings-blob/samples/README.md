---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-functions
  - azure-functions-extensions
  - azurefunctions-extensions-bindings-blob
urlFragment: extension-blob-samples
---

# Azure Functions Extension Blob library for Python samples

These are code samples that show common scenario operations with the Azure Functions Extension Blob library.

These samples relate to the Azure Storage Blob client library being used as part of a Python Function App. For
examples on how to use the Azure Storage Blob client library, please see [Azure Storage Blob samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob/samples)

* [blob_samples_blobclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_blobclient)  - Examples for using the BlobClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_containerclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_containerclient) - Examples for using the ContainerClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_storagestreamdownloader](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-bindings-blob/samples/blob_samples_storagestreamdownloader) - Examples for using the StorageStreamDownloader type:
    * From BlobTrigger
    * From BlobInput

## Prerequisites
* Python 3.9 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).
* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an
[Azure storage account](https://docs.microsoft.com/azure/storage/common/storage-account-overview) to use this package.

## Setup

1. Install [Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python)
2. Install the Azure Functions Extension Blob library for Python with [pip](https://pypi.org/project/pip/):

```bash
pip install azurefunctions-extensions-bindings-blob
```

3. Clone or download this sample repository
4. Open the sample folder in Visual Studio Code or your IDE of choice.

## Running the samples

1. Open a terminal window and `cd` to the directory that the sample you wish to run is saved in.
2. Set the environment variables specified in the sample file you wish to run.
3. Install the required dependencies
```bash
pip install -r requirements.txt
```
4. Start the Functions runtime
```bash
func start
```
5. Execute the function by either sending an HTTP request to the local endpoint or uploading a blob to the specified directory,
based on the type of function you wish to execute.

## Next steps

Visit the [SDK-type bindings in Python reference documentation]() to learn more about how to use SDK-type bindings in a Python Function App and the
[API reference documentation](https://aka.ms/azsdk-python-storage-blob-ref) to learn more about
what you can do with the Azure Storage Blob client library.