# Azure Functions Extensions Bindings EventHub library for Python
This library allows an EventHub Trigger binding in Python Function Apps to recognize and bind to the types from the
Azure EventHub sdk (EventData).

EventHub types can be generated from:

* EventHub Triggers

The supported EventHub SDK types include:

* EventData

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-eventhub)
[Package (PyPi)](https://pypi.org/project/azurefunctions-extensions-bindings-eventhub/)
| [Samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-eventhub/samples)


## Getting started

### Prerequisites
* Python 3.10 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an
[Azure storage account](https://docs.microsoft.com/azure/storage/common/storage-account-overview) to use this package.

### Install the package
Install the Azure Functions Extensions Bindings EventHub library for Python with pip:

```bash
pip install azurefunctions-extensions-bindings-eventhub
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
The Azure Functions Extensions Bindings EventHub library for Python allows you to create a function app with an EventHub Trigger
and define the type as an EventData. Instead of receiving an EventHubEvent, when the function is executed, the type returned will be the defined SDK-type and have all of the properties and methods available as seen in the Azure EventHub library for Python.


```python
import logging
import azure.functions as func
import azurefunctions.extensions.bindings.eventhub as eh

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.event_hub_message_trigger(
    arg_name="event", event_hub_name="EVENTHUB_NAME", connection="AzureWebJobsStorage"
) 
def eventhub_trigger(event: eh.EventData):
    logging.info(
        "Python EventHub trigger processed an event %s",
        event.body_as_str()
    )


@app.event_hub_message_trigger(
    arg_name="events", event_hub_name="EVENTHUB_NAME", connection="AzureWebJobsStorage", cardinality="many"
)
def eventhub_trigger(events: List[eh.EventData]):
    for event in events:
        logging.info(
            "Python EventHub trigger processed an event %s",
            event.body_as_str()
        )
```

## Troubleshooting
### General
The SDK-types raise exceptions defined in [Azure Core](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md).

This list can be used for reference to catch thrown exceptions. To get the specific error code of the exception, use the `error_code` attribute, i.e, `exception.error_code`.

## Next steps

### More sample code

Get started with our [EventHub samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-eventhub/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with EventHubs:

* [eventhub_samples_eventdata](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-eventhub/samples/eventhub_samples_eventdata)  - Examples for using the EventData type:
    * From EventHubTrigger

### Additional documentation
For more information on the Azure EventHub SDK, see the [Azure EventHub documentation](https://learn.microsoft.com/en-us/azure/event-hubs/) on learn.microsoft.com
and the [Azure EventHub README](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/eventhub/azure-eventhub/README.md).

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.