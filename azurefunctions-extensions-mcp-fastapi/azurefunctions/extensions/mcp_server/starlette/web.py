#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Callable

import uvicorn
from azurefunctions.extensions.base import (
    RequestSynchronizer,
    RequestTrackerMeta,
    ResponseLabels,
    ResponseTrackerMeta,
    WebApp,
    WebServer,
)

from starlette.applications import Starlette

from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.responses import FileResponse as StarletteFileResponse
from starlette.responses import HTMLResponse as StarletteHTMLResponse
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.responses import PlainTextResponse as StarlettePlainTextResponse
from starlette.responses import RedirectResponse as StarletteRedirectResponse
from starlette.responses import StreamingResponse as StarletteStreamingResponse

from pydantic import BaseModel

import logging


class RequestSynchronizer(RequestSynchronizer):
    def sync_route_params(self, request, path_params):
        # add null checks for request and path_params
        if request is None:
            raise TypeError("Request object is None")
        if path_params is None:
            raise TypeError("Path parameters are None")

        request.path_params.clear()
        request.path_params.update(path_params)


class Request(metaclass=RequestTrackerMeta):
    request_type = StarletteRequest
    synchronizer = RequestSynchronizer()


class Response(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.STANDARD
    response_type = StarletteResponse


class StreamingResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.STREAMING
    response_type = StarletteStreamingResponse


class HTMLResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.HTML
    response_type = StarletteHTMLResponse


class PlainTextResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.PLAIN_TEXT
    response_type = StarlettePlainTextResponse


class RedirectResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.REDIRECT
    response_type = StarletteRedirectResponse


class JSONResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.JSON
    response_type = StarletteJSONResponse


class FileResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.FILE
    response_type = StarletteFileResponse


class StrResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.STR
    response_type = str


class DictResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.DICT
    response_type = dict


class BoolResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.BOOL
    response_type = bool


class PydanticResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.PYDANTIC
    response_type = BaseModel


class IntResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.INT
    response_type = int


class FloatResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.FLOAT
    response_type = float


class ListResponse(metaclass=ResponseTrackerMeta):
    label = ResponseLabels.LIST
    response_type = list


class WebApp(WebApp):
    def __init__(self):
        self.web_app = Starlette(debug=True)

    def route(self, func: Callable):
        # Apply the api_route decorator
        self.web_app.add_route(route=func, path="/{path:path}", methods=[
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "HEAD",
                "PATCH",
                "TRACE",
            ])

    def get_app(self):
        return self.web_app


class WebServer(WebServer):
    async def serve(self):
        uvicorn_config = uvicorn.Config(
            self.web_app, host=self.hostname, port=self.port, loop="asyncio", log_level="debug", lifespan="on", use_colors=True
        )
        logging.info(f"Starting server on {self.hostname}:{self.port}")
        # Create a Uvicorn server instance
        server = uvicorn.Server(uvicorn_config)

        return await server.serve()
