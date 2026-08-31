---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-functions
  - azure-functions-extensions
  - azurefunctions-extensions-bindings-eventhub
urlFragment: extension-eventhub-samples
---

# Azure Functions Extension EventHub library for Python samples

These are code samples that show common scenario operations with the Azure Functions Extension EventHub library.

These samples relate to the Azure EventHub library being used as part of a Python Function App. For
examples on how to use the Azure EventHub library, please see [Azure EventHub samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/eventhub/azure-eventhub/samples).

* [eventhub_samples_eventdata](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-eventhub/samples/eventhub_samples_eventdata)  - Examples for using the EventData type:
    * From EventHubTrigger

## Prerequisites
* Python 3.9 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).
* You must have an [Azure subscription](https://azure.microsoft.com/free/), an
[Azure Event Hubs namespace, and an event hub](https://learn.microsoft.com/azure/event-hubs/event-hubs-create) to use these samples.
* You must run [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) or configure an Azure storage account for the Functions host.

## Setup

1. Install [Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python)
2. Install the Azure Functions Extension EventHub library for Python with [pip](https://pypi.org/project/pip/):

```bash
pip install azurefunctions-extensions-bindings-eventhub
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
5. Execute the function by uploading an event to the EventHub that is being targeted.

## Next steps

Visit the [SDK-type bindings in Python reference documentation](https://learn.microsoft.com/azure/azure-functions/functions-reference-python?pivots=python-mode-decorators#sdk-type-bindings) to learn more about how to use SDK-type bindings in a Python Function App and the
[API reference documentation](https://learn.microsoft.com/python/api/azure-eventhub/azure.eventhub?view=azure-python) to learn more about
what you can do with the Azure EventHub library.
