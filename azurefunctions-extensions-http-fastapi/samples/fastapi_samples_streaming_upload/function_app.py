# This Azure Function receives streaming data from a client and processes it in real-time.
# It demonstrates streaming upload capabilities for scenarios such as uploading large files,
# processing continuous data streams, or handling IoT device data.

import azure.functions as func
from azurefunctions.extensions.http.fastapi import JSONResponse, Request

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
