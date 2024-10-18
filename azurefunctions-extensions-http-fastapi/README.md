# Azure Functions Extensions Http FastApi library for Python
This library contains HttpV2 extensions for FastApi Request/Response types to use in your function app code. 

[Source code](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-http-fastapi)
| [Package (PyPi)](https://pypi.org/project/azurefunctions-extensions-http-fastapi/)
| API reference documentation
| Product documentation
| [Samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-http-fastapi/samples)


## Getting started

### Prerequisites
* Python 3.8 or later is required to use this package. For more details, please read our page on [Python Functions version support policy](https://learn.microsoft.com/en-us/azure/azure-functions/functions-versions?tabs=isolated-process%2Cv4&pivots=programming-language-python#languages).


### Instructions
1. Follow the guide to [create an app](https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?tabs=windows%2Cbash%2Cazure-cli%2Cbrowser). If you're testing the function locally, make sure to update to the latest version of Core Tools.
2. Ensure your app is using programming model v2 and contains a http trigger function.
3. Add ```azurefunctions-extensions-http-fastapi``` to your requirements.txt
4. Import Request and different types of responses from ```azurefunctions.extensions.http.fastapi``` in your HttpTrigger functions.
5. Change the request and response types to ones imported from ```azurefunctions.extensions.http.fastapi```.
6. Add ```"PYTHON_ENABLE_INIT_INDEXING": "1"``` to your local.settings.json file or App Settings.
6. Run your function app and try it out!

### Bind to the FastApi-type
The Azure Functions Extensions Http FastApi library for Python allows you to create a function app with FastApi Request or Response types. When your function runs, you will receive the request of FastApi Request type and you can return a FastApi response type instance. FastApi is one of top popular python web framework which provides elegant and powerful request/response types and functionalities to users. With this integration, you are empowered to use request/response the same way as using them in native FastApi. A good example is you can do http streaming upload and streaming download now! Feel free to check out [Fastapi doc](https://fastapi.tiangolo.com/reference/responses/?h=custom) for further reference. 


```python
# This Azure Function receives streaming data from a client and processes it in real-time.
# It demonstrates streaming upload capabilities for scenarios such as uploading large files,
# processing continuous data streams, or handling IoT device data.

import azure.functions as func
from azurefunctions.extensions.http.fastapi import Request, JSONResponse

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="streaming_upload", methods=[func.HttpMethod.POST])
async def streaming_upload(req: Request) -> JSONResponse:
    """Handle streaming upload requests."""
    # Process each chunk of data as it arrives
    async for chunk in req.stream():
        process_data_chunk(chunk)

    # Once all data is received, return a JSON response indicating successful processing
    return JSONResponse({"status": "Data uploaded and processed successfully"})

def process_data_chunk(chunk: bytes):
    """Process each data chunk."""
    # Add custom processing logic here
    pass
```

## Next steps

### More sample code

Get started with our [FastApi samples](hhttps://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-http-fastapi/samples).

Several samples are available in this GitHub repository. These samples provide example code for additional scenarios commonly encountered while working with FastApi:

* [fastapi_samples_streaming_upload](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-http-fastapi/samples/fastapi_samples_streaming_upload) - An example on how to send and receiving a streaming request within your function.

* [fastapi_samples_streaming_download](https://github.com/Azure/azure-functions-python-extensions/tree/main/azurefunctions-extensions-http-fastapi/samples/fastapi_samples_streaming_download) - An example on how  to send your http response via streaming to the caller.t

## Contributing
This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
