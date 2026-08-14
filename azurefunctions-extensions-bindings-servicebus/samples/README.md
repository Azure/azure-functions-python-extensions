---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-functions
  - azure-functions-extensions
  - azurefunctions-extensions-bindings-servicebus
urlFragment: extension-servicebus-samples
---

# Azure Functions Extension ServiceBus library for Python samples

These are code samples that show common scenario operations with the Azure Functions Extension ServiceBus library.

These samples relate to the Azure ServiceBus client library being used as part of a Python Function App. For
examples on how to use the Azure ServiceBus client library, please see [Azure ServiceBus samples](https://github.com/Azure/azure-sdk-for-python/tree/azure-servicebus_7.14.1/sdk/servicebus/azure-servicebus/samples)

* [servicebus_samples_single](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples/servicebus_samples_single)  - Examples for using the ServiceBusReceivedMessage type:
    * From ServiceBus Queue Trigger (Single Message)
    * From ServiceBus Topic Trigger (Single Message)
* [servicebus_samples_batch](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples/servicebus_samples_batch)  - Examples for using the ServiceBusReceivedMessage type:
    * From ServiceBus Queue Trigger (Batch)
    * From ServiceBus Topic Trigger (Batch)


## Prerequisites
* Python 3.9 through 3.13 is required to use these samples. Python 3.14 is not currently supported because `uamqp` does not publish Python 3.14 wheels. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

## Setup

1. Install [Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python)
2. Install the Azure Functions Extension ServiceBus library for Python with [pip](https://pypi.org/project/pip/):

```bash
pip install azurefunctions-extensions-bindings-servicebus
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
5. Execute the function by triggering the ServiceBus entity.

## Next steps

Visit the [SDK-type bindings in Python reference documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=get-started%2Casgi%2Capplication-level&pivots=python-mode-decorators#sdk-type-bindings-preview) to learn more about how to use SDK-type bindings in a Python Function App and the
[API reference documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/service-bus?view=azure-python) to learn more about
what you can do with the Azure ServiceBus client library.