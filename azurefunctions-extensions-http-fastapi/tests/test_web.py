import asyncio
import unittest
from unittest.mock import MagicMock, patch

from azurefunctions.extensions.base import (
    RequestTrackerMeta,
    ResponseLabels,
    ResponseTrackerMeta,
)
from azurefunctions.extensions.http.fastapi import (
    RequestSynchronizer,
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


class TestRequestTrackerMeta(unittest.TestCase):
    def test_request_type_defined(self):
        class Request(metaclass=RequestTrackerMeta):
            request_type = FastApiRequest
            synchronizer = RequestSynchronizer()

        self.assertTrue(hasattr(Request, "request_type"))
        self.assertEqual(Request.request_type, FastApiRequest)

    def test_request_type_undefined(self):
        with self.assertRaises(Exception) as context:

            class Request(metaclass=RequestTrackerMeta):
                pass

        self.assertTrue("Request type not provided" in str(context.exception))


class TestResponseTrackerMeta(unittest.TestCase):
    def test_response_labels_defined(self):
        class Response(metaclass=ResponseTrackerMeta):
            label = ResponseLabels.STANDARD
            response_type = FastApiResponse

        self.assertTrue(hasattr(Response, "label"))
        self.assertTrue(hasattr(Response, "response_type"))
        self.assertEqual(Response.label, ResponseLabels.STANDARD)
        self.assertEqual(Response.response_type, FastApiResponse)

    def test_response_labels_undefined(self):
        with self.assertRaises(Exception) as context:

            class Response(metaclass=ResponseTrackerMeta):
                pass

        self.assertTrue("Response label not provided" in str(context.exception))

    def test_multiple_response_labels(self):
        with self.assertRaises(Exception) as context:

            class Response1(metaclass=ResponseTrackerMeta):
                label = ResponseLabels.STANDARD
                response_type = FastApiResponse

            class Response2(metaclass=ResponseTrackerMeta):
                label = ResponseLabels.STANDARD
                response_type = FastApiJSONResponse

        self.assertTrue(
            "Only one response type shall be recorded" in str(context.exception)
        )


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.web_app = WebApp()

    def test_route(self):
        @self.web_app.route
        def test_route(request: FastApiRequest):
            return {"message": "Hello"}

        self.assertTrue(
            "/{path:path}"
            in [endpoint.path for endpoint in self.web_app.web_app.router.routes]
        )
        route = [
            endpoint
            for endpoint in self.web_app.web_app.router.routes
            if endpoint.path == "/{path:path}"
        ][0]
        self.assertEqual(
            route.methods,
            {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"},
        )

    def test_get_app(self):
        self.assertIsInstance(self.web_app.get_app(), FastAPI)


class TestWebServer(unittest.TestCase):
    def setUp(self):
        class TestApp:
            pass

        self.test_app = TestApp()
        self.web_app_mock = MagicMock().get_app()
        self.web_app_mock.get_app.return_value = self.test_app
        self.hostname = "localhost"
        self.port = 8000
        self.web_server = WebServer(self.hostname, self.port, self.web_app_mock)

    @patch("uvicorn.Config")
    @patch("uvicorn.Server")
    def test_serve(self, server_mock, config_mock):
        async def serve():
            await asyncio.sleep(0)

        config_instance_mock = config_mock.return_value
        server_instance_mock = server_mock.return_value
        server_instance_mock.serve = (
            serve  # Mock the serve method to return a CoroutineMock
        )

        asyncio.get_event_loop().run_until_complete(self.web_server.serve())

        config_mock.assert_called_once_with(
            self.test_app, host=self.hostname, port=self.port
        )
        server_mock.assert_called_once_with(config_instance_mock)

    async def run_serve(self):
        await self.web_server.serve()


class TestRequestSynchronizer(unittest.TestCase):
    def test_sync_route_params(self):
        # Create a mock request object
        mock_request = MagicMock()

        # Define some path parameters
        path_params = {"param1": "value1", "param2": "value2"}

        # Create an instance of the ConcreteRequestSynchronizer
        synchronizer = RequestSynchronizer()

        # Call the sync_route_params method with the mock request and path parameters
        synchronizer.sync_route_params(mock_request, path_params)

        # Assert that the request's path_params have been updated with the provided path parameters
        mock_request.path_params.clear.assert_called_once()
        mock_request.path_params.update.assert_called_once_with(path_params)

    def test_sync_route_params_missing_request(self):
        # Create an instance of the ConcreteRequestSynchronizer
        synchronizer = RequestSynchronizer()

        # Define some path parameters
        path_params = {"param1": "value1", "param2": "value2"}

        # Call the sync_route_params method with a None request and path parameters
        with self.assertRaises(TypeError):
            synchronizer.sync_route_params(None, path_params)

    def test_sync_route_params_missing_path_params(self):
        # Create a mock request object
        mock_request = MagicMock()

        # Create an instance of the ConcreteRequestSynchronizer
        synchronizer = RequestSynchronizer()

        # Call the sync_route_params method with the mock request and None path parameters
        with self.assertRaises(TypeError):
            synchronizer.sync_route_params(mock_request, None)


class TestExtensionClasses(unittest.TestCase):
    def test_request(self):
        from azurefunctions.extensions.http.fastapi.web import Request

        self.assertEqual(RequestTrackerMeta.get_request_type(), FastApiRequest)
        self.assertTrue(
            isinstance(RequestTrackerMeta.get_synchronizer(), RequestSynchronizer)
        )

    def test_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.STANDARD),
            FastApiResponse,
        )

    def test_streaming_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.STREAMING),
            FastApiStreamingResponse,
        )

    def test_html_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.HTML),
            FastApiHTMLResponse,
        )

    def test_plain_text_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.PLAIN_TEXT),
            FastApiPlainTextResponse,
        )

    def test_redirect_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.REDIRECT),
            FastApiRedirectResponse,
        )

    def test_json_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.JSON),
            FastApiJSONResponse,
        )

    def test_ujson_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.UJSON),
            FastApiUJSONResponse,
        )

    def test_orjson_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.ORJSON),
            FastApiORJSONResponse,
        )

    def test_file_response(self):
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.FILE),
            FastApiFileResponse,
        )
