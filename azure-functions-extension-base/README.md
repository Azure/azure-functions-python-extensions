# Azure Functions Extension Base library for Python
This is the base library for allowing Python Function Apps to recognize and bind to SDk-types. It is not to be used directly.
Instead, please reference one of the extending packages.

Currently, the supported SDK-type bindings are:

* Azure Storage Blob

## Next steps

### More sample code

Get started with our [Blob samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azure-functions-extension-blob/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with Storage Blobs:

* [blob_samples_blobclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azure-functions-extension-blob/samples/blob_samples_blobclient)  - Examples for using the BlobClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_containerclient](https://github.com/Azure/azure-functions-python-extensions/tree/main/azure-functions-extension-blob/samples/blob_samples_containerclient) - Examples for using the ContainerClient type:
    * From BlobTrigger
    * From BlobInput

* [blob_samples_storagestreamdownloader](https://github.com/Azure/azure-functions-python-extensions/tree/main/azure-functions-extension-blob/samples/blob_samples_storagestreamdownloader) - Examples for using the StorageStreamDownloader type:
    * From BlobTrigger
    * From BlobInput

### Additional documentation
For more information on the Azure Storage Blob SDK, see the [Azure Blob storage documentation](https://docs.microsoft.com/azure/storage/blobs/) on docs.microsoft.com
and the [Azure Storage Blobs README](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob).

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.