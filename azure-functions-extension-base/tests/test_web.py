import unittest
from unittest.mock import patch

from azure.functions.extension.base import (
    HttpV2FeatureChecker,
    ModuleTrackerMeta,
    RequestTrackerMeta,
    ResponseLabels,
    ResponseTrackerMeta,
    WebApp,
    WebServer,
)


class TestModuleTrackerMeta(unittest.TestCase):
    def setUp(self):
        # Reset the _module attribute after each test
        ModuleTrackerMeta._module = None
        self.assertFalse(HttpV2FeatureChecker.http_v2_enabled())

    def test_classes_imported_from_same_module(self):
        class TestClass1(metaclass=ModuleTrackerMeta):
            pass

        class TestClass2(metaclass=ModuleTrackerMeta):
            pass

        self.assertEqual(ModuleTrackerMeta.get_module(), __name__)
        self.assertTrue(ModuleTrackerMeta.module_imported())
        self.assertTrue(HttpV2FeatureChecker.http_v2_enabled())

    def test_class_imported_from_a_module(self):
        class TestClass1(metaclass=ModuleTrackerMeta):
            pass

        self.assertEqual(ModuleTrackerMeta.get_module(), __name__)
        self.assertTrue(ModuleTrackerMeta.module_imported())
        self.assertTrue(HttpV2FeatureChecker.http_v2_enabled())

    def test_classes_imported_from_different_modules(self):
        class TestClass1(metaclass=ModuleTrackerMeta):
            __module__ = "module1"

        self.assertEqual(ModuleTrackerMeta.get_module(), "module1")
        self.assertTrue(ModuleTrackerMeta.module_imported())

        with self.assertRaises(Exception) as context:

            class TestClass2(metaclass=ModuleTrackerMeta):
                __module__ = "module2"

        self.assertEqual(
            str(context.exception),
            "Only one web extension package shall be imported, "
            "module1 and module2 are imported",
        )


class TestRequestTrackerMeta(unittest.TestCase):
    class TestRequest1:
        pass

    class TestRequest2:
        pass

    class TestRequest3:
        pass

    def setUp(self):
        # Reset _request_type before each test
        RequestTrackerMeta._request_type = None

    def test_request_type_not_provided(self):
        # Define a class without providing the request_type attribute
        with self.assertRaises(Exception) as context:

            class TestClass(metaclass=RequestTrackerMeta):
                pass

        self.assertEqual(
            str(context.exception), "Request type not provided for class TestClass"
        )

    def test_single_request_type(self):
        # Define a class providing a request_type attribute
        class TestClass(metaclass=RequestTrackerMeta):
            request_type = self.TestRequest1

        # Ensure the request_type is correctly recorded
        self.assertEqual(RequestTrackerMeta.get_request_type(), self.TestRequest1)
        # Ensure check_type returns True for the provided request_type
        self.assertTrue(RequestTrackerMeta.check_type(self.TestRequest1))

    def test_multiple_request_types_same(self):
        # Define a class providing the same request_type attribute
        class TestClass1(metaclass=RequestTrackerMeta):
            request_type = self.TestRequest1

        # Ensure the request_type is correctly recorded
        self.assertEqual(RequestTrackerMeta.get_request_type(), self.TestRequest1)
        # Ensure check_type returns True for the provided request_type
        self.assertTrue(RequestTrackerMeta.check_type(self.TestRequest1))

        # Define another class providing the same request_type attribute
        class TestClass2(metaclass=RequestTrackerMeta):
            request_type = self.TestRequest1

        # Ensure the request_type remains the same
        self.assertEqual(RequestTrackerMeta.get_request_type(), self.TestRequest1)
        # Ensure check_type still returns True for the original request_type
        self.assertTrue(RequestTrackerMeta.check_type(self.TestRequest1))

    def test_multiple_request_types_different(self):
        # Define a class providing a different request_type attribute
        class TestClass1(metaclass=RequestTrackerMeta):
            request_type = self.TestRequest1

        # Ensure the request_type is correctly recorded
        self.assertEqual(RequestTrackerMeta.get_request_type(), self.TestRequest1)
        # Ensure check_type returns True for the provided request_type
        self.assertTrue(RequestTrackerMeta.check_type(self.TestRequest1))

        # Define another class providing a different request_type attribute
        with self.assertRaises(Exception) as context:

            class TestClass2(metaclass=RequestTrackerMeta):
                request_type = self.TestRequest2

        self.assertEqual(
            str(context.exception),
            f"Only one request type shall be recorded for class TestClass2"
            f" but found {self.TestRequest1} and {self.TestRequest2}",
        )

        # Ensure the request_type remains the same after the exception
        self.assertEqual(RequestTrackerMeta.get_request_type(), self.TestRequest1)
        # Ensure check_type still returns True for the original request_type
        self.assertTrue(RequestTrackerMeta.check_type(self.TestRequest1))


class TestResponseTrackerMeta(unittest.TestCase):
    class MockResponse1:
        pass

    class MockResponse2:
        pass

    def test_classes_imported_from_same_module(self):
        class TestResponse1(metaclass=ResponseTrackerMeta):
            label = "test_label_1"
            response_type = self.MockResponse1

        class TestResponse2(metaclass=ResponseTrackerMeta):
            label = "test_label_2"
            response_type = self.MockResponse2

        self.assertEqual(
            ResponseTrackerMeta.get_response_type("test_label_1"), self.MockResponse1
        )
        self.assertEqual(
            ResponseTrackerMeta.get_response_type("test_label_2"), self.MockResponse2
        )
        self.assertIsNone(ResponseTrackerMeta.get_response_type("non_existing_label"))
        self.assertTrue(ResponseTrackerMeta.check_type(self.MockResponse1))
        self.assertTrue(ResponseTrackerMeta.check_type(self.MockResponse2))

    def test_class_imported_from_a_module(self):
        class TestResponse1(metaclass=ResponseTrackerMeta):
            label = "test_label_1"
            response_type = self.MockResponse1

        self.assertEqual(
            ResponseTrackerMeta.get_response_type("test_label_1"), self.MockResponse1
        )
        self.assertIsNone(ResponseTrackerMeta.get_response_type("non_existing_label"))
        self.assertTrue(ResponseTrackerMeta.check_type(self.MockResponse1))
        self.assertFalse(ResponseTrackerMeta.check_type(self.MockResponse2))

    def test_classes_imported_from_different_modules(self):
        class TestResponse1(metaclass=ResponseTrackerMeta):
            __module__ = "module1"
            label = "test_label_1"
            response_type = self.MockResponse1

        with self.assertRaises(Exception) as context:

            class TestResponse2(metaclass=ResponseTrackerMeta):
                __module__ = "module2"
                label = "test_label_1"
                response_type = self.MockResponse2

        self.assertEqual(
            str(context.exception),
            "Only one response type shall be recorded for class TestResponse2 "
            f"but found {self.MockResponse1} and {self.MockResponse2}",
        )

    def test_different_labels(self):
        class TestResponse1(metaclass=ResponseTrackerMeta):
            label = ResponseLabels.STANDARD
            response_type = self.MockResponse1

        class TestResponse2(metaclass=ResponseTrackerMeta):
            label = ResponseLabels.STREAMING
            response_type = self.MockResponse2

        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.STANDARD),
            self.MockResponse1,
        )
        self.assertEqual(
            ResponseTrackerMeta.get_response_type(ResponseLabels.STREAMING),
            self.MockResponse2,
        )
        self.assertTrue(ResponseTrackerMeta.check_type(self.MockResponse1))
        self.assertTrue(ResponseTrackerMeta.check_type(self.MockResponse2))


class TestWebApp(unittest.TestCase):
    def test_route_and_get_app(self):
        class MockWebApp(WebApp):
            def route(self, func):
                return

            def get_app(self):
                return "MockApp"

        app = MockWebApp()
        self.assertEqual(app.get_app(), "MockApp")


class TestWebServer(unittest.TestCase):
    def test_web_server_initialization(self):
        class MockWebApp(WebApp):
            def route(self, func):
                pass

            def get_app(self):
                return "MockApp"

        mock_web_app = MockWebApp()
        server = WebServer("localhost", 8080, mock_web_app)
        self.assertEqual(server.hostname, "localhost")
        self.assertEqual(server.port, 8080)
        self.assertEqual(server.web_app, "MockApp")


class TestHttpV2Enabled(unittest.TestCase):
    @patch("azure.functions.extension.base.ModuleTrackerMeta.module_imported")
    def test_http_v2_enabled(self, mock_module_imported):
        mock_module_imported.return_value = True
        self.assertTrue(HttpV2FeatureChecker.http_v2_enabled())

        mock_module_imported.return_value = False
        self.assertFalse(HttpV2FeatureChecker.http_v2_enabled())
