# Azure Functions Extensions Bindings ServiceBus library for Python
This library allows ServiceBus Triggers in Python Function Apps to recognize and bind to client types from the
Azure ServiceBus sdk.

The SDK types can be generated from:

* ServiceBus Triggers

The supported ServiceBus SDK types include:

* ServiceBusReceivedMessage

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus)
| 
[Package (PyPi)](https://pypi.org/project/azurefunctions-extensions-bindings-servicebus/)
| [Samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples)


## Getting started

### Prerequisites
* Python 3.10 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and a
[ServiceBus Resource](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-service-bus?tabs=isolated-process%2Cextensionv5%2Cextensionv3&pivots=programming-language-python) to use this package.

### Install the package
Install the Azure Functions Extensions Bindings ServiceBus library for Python with pip:

```bash
pip install azurefunctions-extensions-bindings-servicebus
```


### Bind to the SDK-type
The Azure Functions Extensions Bindings ServiceBus library for Python allows you to create a function app with a ServiceBus Trigger
and define the type as a ServiceBusReceivedMessage. Instead of receiving
a ServiceBusMessage, when the function is executed, the type returned will be the defined SDK-type and have all the
properties and methods available as seen in the Azure ServiceBus library for Python.


```python
import logging
import azure.functions as func
import azurefunctions.extensions.bindings.servicebus as servicebus

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.service_bus_queue_trigger(arg_name="receivedmessage",
                               queue_name="QUEUE_NAME",
                               connection="SERVICEBUS_CONNECTION")
def servicebus_queue_trigger(receivedmessage: servicebus.ServiceBusReceivedMessage):
    logging.info("Python ServiceBus queue trigger processed message.")
    logging.info("Receiving: %s\n"
                 "Body: %s\n"
                 "Enqueued time: %s\n"
                 "Lock Token: %s\n"
                 "Locked until : %s\n"
                 "Message ID: %s\n"
                 "Sequence number: %s\n",
                 receivedmessage,
                 receivedmessage.body,
                 receivedmessage.enqueued_time_utc,
                 receivedmessage.lock_token,
                 receivedmessage.locked_until,
                 receivedmessage.message_id,
                 receivedmessage.sequence_number)
```

## Troubleshooting
### General
The SDK-types raise exceptions defined in [Azure Core](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md).

This list can be used for reference to catch thrown exceptions. To get the specific error code of the exception, use the `error_code` attribute, i.e, `exception.error_code`.

## Next steps

### More sample code

Get started with our [ServiceBus samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with Azure ServiceBus:

* [servicebus_samples_single](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples/servicebus_samples_single)  - Examples for using the ServiceBusReceivedMessage type:
    * From ServiceBus Queue Trigger (Single Message)
    * From ServiceBus Topic Trigger (Single Message)

* [servicebus_samples_batch](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-bindings-servicebus/samples/service_samples_batch) - Examples for interacting with batches:
    * From ServiceBus Queue Trigger (Batch)
    * From ServiceBus Topic Trigger (Batch)


### Additional documentation
For more information on the Azure ServiceBus SDK, see the [Azure ServiceBus SDK documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/servicebus-readme?view=azure-python) on docs.microsoft.com
and the [Azure ServiceBus README](https://github.com/Azure/azure-sdk-for-python/blob/azure-servicebus_7.14.1/sdk/servicebus/azure-servicebus/README.md).

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.