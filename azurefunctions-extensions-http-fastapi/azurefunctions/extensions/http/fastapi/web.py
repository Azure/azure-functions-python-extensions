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
from pydantic import BaseModel


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
    request_type = FastApiRequest
    synchronizer = RequestSynchronizer()


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
