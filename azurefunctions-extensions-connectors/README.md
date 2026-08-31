# Azure Functions Extensions Connectors library for Python

This library allows Office365 Connector Triggers in Python Function Apps to recognize and bind to client types from the Azure Connectors SDK.

Office365 client types can be generated from:

* Office365 Connector Triggers

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-connectors)
| [Package (PyPI)](https://pypi.org/project/azurefunctions-extensions-connectors/)
| [Samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-connectors/samples)


## Getting started

### Prerequisites
* Python 3.10 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

* You must have an [Azure subscription](https://azure.microsoft.com/free/) and an Office365 account to use this package.

### Install the package
Install the Azure Functions Extensions Connectors Office365 library for Python with pip:

```bash
pip install azurefunctions-extensions-connectors
```

### Bind to the SDK-type
The Azure Functions Extensions Connectors Office365 library for Python allows you to create a function app with an Office365 Connector Trigger and define the type as a ClientReceiveMessage or List[ClientReceiveMessage]. Instead of receiving raw data, when the function is executed, the type returned will be the defined SDK-type and have all of the methods available from the `azure-connectors` SDK.

## Key concepts

### ClientReceiveMessage
The `ClientReceiveMessage` type represents a message received from an Office365 connector. The extension automatically parses the incoming JSON payload and converts it into typed ClientReceiveMessage objects from the `azure-connectors` SDK.

### Cardinality
Office365 Connector Triggers support both single and batch message processing:

* **Single message (cardinality=one)**: Annotate your function parameter as `ClientReceiveMessage` to receive one message per function invocation
* **Batch messages (cardinality=many)**: Annotate your function parameter as `List[ClientReceiveMessage]` to receive multiple messages in a single function invocation

## Examples

### Office365 Connector Trigger - Single Message

```python
import logging
import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365

app = func.FunctionApp()

@app.connector_trigger(arg_name="message", connection="OFFICE365_CONNECTION")
def office365_trigger_single(message: office365.ClientReceiveMessage):
    logging.info(f"Received Office365 message: {message}")
    # Access message properties using the Azure Connectors SDK methods
```

### Office365 Connector Trigger - Batch Messages

```python
import logging
from typing import List
import azure.functions as func
import azurefunctions.extensions.connectors.office365 as office365

app = func.FunctionApp()

@app.connector_trigger(arg_name="messages", connection="OFFICE365_CONNECTION")
def office365_trigger_batch(messages: List[office365.ClientReceiveMessage]):
    logging.info(f"Received {len(messages)} Office365 messages")
    for message in messages:
        logging.info(f"Processing message: {message}")
        # Access message properties using the Azure Connectors SDK methods
```

## Troubleshooting

### General
Office365 Connector extension errors will be raised as `ValueError` exceptions with descriptive error messages.

### Logging
Enable verbose logging in your function app to see detailed information about message processing:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Next steps

### More sample code
Get started with our [Office365 Connector samples](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-connectors/samples).

## Contributing
This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
