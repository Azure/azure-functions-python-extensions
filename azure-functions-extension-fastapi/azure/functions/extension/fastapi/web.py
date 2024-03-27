#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Callable

import uvicorn
from azure.functions.extension.base import (
    RequestTrackerMeta,
    ResponseLabels,
    ResponseTrackerMeta,
    WebApp,
    WebServer,
)
from fastapi import FastAPI
from fastapi import Request as FastApiRequest
from fastapi import Response as FastApiResponse
from fastapi.responses import FileResponse as FastApiFileResponse
from fastapi.responses import HTMLResponse as FastApiHTMLResponse
from fastapi.responses import JSONResponse as FastApiJSONResponse
from fastapi.responses import ORJSONResponse as FastApiORJSONResponse
from fastapi.responses import PlainTextResponse as FastApiPlainTextResponse
from fastapi.responses import RedirectResponse as FastApiRedirectResponse
from fastapi.responses import StreamingResponse as FastApiStreamingResponse
from fastapi.responses import UJSONResponse as FastApiUJSONResponse


class Request(metaclass=RequestTrackerMeta):
    request_type = FastApiRequest


class Response(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.STANDARD
    response_type = FastApiResponse


class StreamingResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.STREAMING
    response_type = FastApiStreamingResponse


class HTMLResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.HTML
    response_type = FastApiHTMLResponse


class PlainTextResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.PLAIN_TEXT
    response_type = FastApiPlainTextResponse


class RedirectResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.REDIRECT
    response_type = FastApiRedirectResponse


class JSONResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.JSON
    response_type = FastApiJSONResponse


class UJSONResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.UJSON
    response_type = FastApiUJSONResponse


class ORJSONResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.ORJSON
    response_type = FastApiORJSONResponse


class FileResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.FILE
    response_type = FastApiFileResponse


class WebApp(WebApp):
    def __init__(self):
        self.web_app = FastAPI()

    def route(self, func: Callable):
        # Apply the api_route decorator
        decorated_function = self.web_app.api_route(
            "/{path:path}",
            methods=[
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "HEAD",
                "PATCH",
                "TRACE",
            ],
        )(func)

        return decorated_function

    def get_app(self):
        return self.web_app


class WebServer(WebServer):
    async def serve(self):
        uvicorn_config = uvicorn.Config(
            self.web_app, host=self.hostname, port=self.port
        )

        server = uvicorn.Server(uvicorn_config)

        return await server.serve()
