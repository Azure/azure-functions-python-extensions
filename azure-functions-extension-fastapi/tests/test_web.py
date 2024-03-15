import asyncio
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from azure.functions.extension.base import ResponseLabels, RequestTrackerMeta, ResponseTrackerMeta
from azure.functions.extension.fastapi import (
    WebApp,
    WebServer,
    Request as FastApiRequest,
    Response as FastApiResponse,
    JSONResponse,
)

class TestRequestTrackerMeta(unittest.TestCase):
    def test_request_type_defined(self):
        class Request(metaclass=RequestTrackerMeta):
            request_type = FastApiRequest

        self.assertTrue(hasattr(Request, 'request_type'))
        self.assertEqual(Request.request_type, FastApiRequest)

    def test_request_type_undefined(self):
        with self.assertRaises(Exception) as context:
            class Request(metaclass=RequestTrackerMeta):
                pass

        self.assertTrue('Request type not provided' in str(context.exception))


class TestResponseTrackerMeta(unittest.TestCase):
    def test_response_labels_defined(self):
        class Response(metaclass=ResponseTrackerMeta):
            label = ResponseLabels.STANDARD
            response_type = FastApiResponse

        self.assertTrue(hasattr(Response, 'label'))
        self.assertTrue(hasattr(Response, 'response_type'))
        self.assertEqual(Response.label, ResponseLabels.STANDARD)
        self.assertEqual(Response.response_type, FastApiResponse)

    def test_response_labels_undefined(self):
        with self.assertRaises(Exception) as context:
            class Response(metaclass=ResponseTrackerMeta):
                pass

        self.assertTrue('Response label not provided' in str(context.exception))

    def test_multiple_response_labels(self):
        with self.assertRaises(Exception) as context:
            class Response1(metaclass=ResponseTrackerMeta):
                label = ResponseLabels.STANDARD
                response_type = FastApiResponse

            class Response2(metaclass=ResponseTrackerMeta):
                label = ResponseLabels.STANDARD
                response_type = JSONResponse

        self.assertTrue('Only one response type shall be recorded' in str(context.exception))


class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.web_app = WebApp()

    def test_route(self):
        @self.web_app.route
        def test_route(request: FastApiRequest):
            return {'message': 'Hello'}

        self.assertTrue('/{path:path}' in [endpoint.path for endpoint in self.web_app.web_app.router.routes])
        route = [endpoint for endpoint in self.web_app.web_app.router.routes if endpoint.path == '/{path:path}'][0]
        self.assertEqual(route.methods, {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"})


    def test_get_app(self):
        self.assertIsInstance(self.web_app.get_app(), FastAPI)

class TestWebServer(unittest.TestCase):
    def setUp(self):
        class TestApp():
            pass
        self.test_app = TestApp()
        self.web_app_mock = MagicMock().get_app()
        self.web_app_mock.get_app.return_value = self.test_app
        self.hostname = 'localhost'
        self.port = 8000
        self.web_server = WebServer(self.hostname, self.port, self.web_app_mock)

    @patch('uvicorn.Config')
    @patch('uvicorn.Server')
    def test_serve(self, server_mock, config_mock):
        async def serve():
            await asyncio.sleep(0)
        config_instance_mock = config_mock.return_value
        server_instance_mock = server_mock.return_value
        server_instance_mock.serve = serve  # Mock the serve method to return a CoroutineMock

        asyncio.get_event_loop().run_until_complete(self.web_server.serve())
        
        config_mock.assert_called_once_with(self.test_app, host=self.hostname, port=self.port)
        server_mock.assert_called_once_with(config_instance_mock)

    async def run_serve(self):
        await self.web_server.serve()