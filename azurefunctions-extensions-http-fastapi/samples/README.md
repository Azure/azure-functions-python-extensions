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

# Azure Functions Extension FastAPI library for Python samples

These are code samples that show common scenario operations with the Azure Functions Extension FastAPI library.

These samples relate to FastApi Request and Response types being used as part of a Python Function App. For
information on FastAPI, please see the [FastApi documentation](https://fastapi.tiangolo.com/reference/responses/?h=custom).

* [fastapi_samples_streaming_upload](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-http-fastapi/samples/fastapi_samples_streaming_upload) - An example on how to send and receive a streaming request within your function.

* [fastapi_samples_streaming_download](https://github.com/Azure/azure-functions-python-extensions/tree/dev/azurefunctions-extensions-http-fastapi/samples/fastapi_samples_streaming_download) - An example on how to send your HTTP response via streaming to the caller.

## Prerequisites
* Python 3.8 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).

## Setup

1. Install [Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python)
2. Install the Azure Functions Extension FastAPI library for Python with [pip](https://pypi.org/project/pip/):

```bash
pip install azurefunctions-extensions-http-fastapi
```

3. Clone or download this sample repository
4. Open the sample folder in Visual Studio Code or your IDE of choice.

## Running the samples

1. Open a terminal window and `cd` to the directory that the sample you wish to run is saved in.
2. Install the required dependencies
```bash
pip install -r requirements.txt
```
3. Start the Functions runtime
```bash
func start
```
4. Execute the function by sending an HTTP request to the local endpoint.

## Next steps

Visit the [HTTP Streams in Python reference documentation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=get-started%2Casgi%2Capplication-level&pivots=python-mode-decorators#http-streams-preview) to learn more about how to use HTTP Streams in a Python Function App and the
[FastApi documentation](https://fastapi.tiangolo.com/reference/responses/?h=custom) to learn more about
what you can do with FastAPI.