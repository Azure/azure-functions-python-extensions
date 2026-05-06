import contextvars
import unittest
from concurrent.futures import ThreadPoolExecutor

from azurefunctions.extensions.base.runtime import (
    RuntimeBase,
    RuntimeFeatureChecker,
    RuntimeTrackerMeta,
)


class TestRuntimeTrackerMeta(unittest.TestCase):
    def setUp(self):
        # Reset the _module and _runtime_name attributes after each test
        RuntimeTrackerMeta._module = None
        RuntimeTrackerMeta._runtime_name = None
        RuntimeTrackerMeta._package_name = None
        self.assertFalse(RuntimeFeatureChecker.runtime_loaded())

    def test_classes_imported_from_same_module(self):
        class TestRuntime1(metaclass=RuntimeTrackerMeta):
            runtime_name = "test_runtime"

        class TestRuntime2(metaclass=RuntimeTrackerMeta):
            runtime_name = "test_runtime"

        self.assertEqual(RuntimeTrackerMeta.get_module(), __name__)
        self.assertEqual(RuntimeTrackerMeta.get_runtime_name(), "test_runtime")
        self.assertTrue(RuntimeTrackerMeta.module_imported())
        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())

    def test_class_imported_from_a_module(self):
        class TestRuntime1(metaclass=RuntimeTrackerMeta):
            runtime_name = "fastapi"

        self.assertEqual(RuntimeTrackerMeta.get_module(), __name__)
        self.assertEqual(RuntimeTrackerMeta.get_runtime_name(), "fastapi")
        self.assertTrue(RuntimeTrackerMeta.module_imported())
        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())

    def test_classes_imported_from_different_modules(self):
        class TestRuntime1(metaclass=RuntimeTrackerMeta):
            __module__ = "module1"
            runtime_name = "fastapi"

        self.assertEqual(RuntimeTrackerMeta.get_module(), "module1")
        self.assertEqual(RuntimeTrackerMeta.get_runtime_name(), "fastapi")
        self.assertTrue(RuntimeTrackerMeta.module_imported())

        with self.assertRaises(Exception) as context:

            class TestRuntime2(metaclass=RuntimeTrackerMeta):
                __module__ = "module2"
                runtime_name = "flask"

        self.assertEqual(
            str(context.exception),
            "Only one runtime package shall be imported at a time. "
            "module1 and module2 are imported.",
        )

    def test_runtime_name_not_set(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            pass

        self.assertEqual(RuntimeTrackerMeta.get_module(), __name__)
        self.assertIsNone(RuntimeTrackerMeta.get_runtime_name())
        self.assertTrue(RuntimeTrackerMeta.module_imported())

    def test_multiple_runtimes_same_name(self):
        class TestRuntime1(metaclass=RuntimeTrackerMeta):
            runtime_name = "fastapi"

        class TestRuntime2(metaclass=RuntimeTrackerMeta):
            runtime_name = "fastapi"

        self.assertEqual(RuntimeTrackerMeta.get_module(), __name__)
        self.assertEqual(RuntimeTrackerMeta.get_runtime_name(), "fastapi")
        self.assertTrue(RuntimeTrackerMeta.module_imported())

    def test_package_name_with_runtime_suffix(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            __module__ = "azurefunctions.extensions.http.fastapi.runtime"
            runtime_name = "fastapi"

        self.assertEqual(
            RuntimeTrackerMeta.get_package_name(),
            "azurefunctions.extensions.http.fastapi",
        )
        self.assertEqual(
            RuntimeTrackerMeta.get_module(),
            "azurefunctions.extensions.http.fastapi.runtime",
        )

    def test_package_name_without_runtime_suffix(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            __module__ = "azurefunctions.extensions.http"
            runtime_name = "test"

        self.assertEqual(RuntimeTrackerMeta.get_package_name(), "azurefunctions")
        self.assertEqual(RuntimeTrackerMeta.get_module(),
                         "azurefunctions.extensions.http")

    def test_package_name_simple_module(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            __module__ = "simplemodule"
            runtime_name = "simple"

        self.assertEqual(RuntimeTrackerMeta.get_package_name(), "simplemodule")
        self.assertEqual(RuntimeTrackerMeta.get_module(), "simplemodule")

    def test_package_name_not_set_before_import(self):
        # Before any runtime is imported, package_name should be None
        self.assertIsNone(RuntimeTrackerMeta.get_package_name())


class TestRuntimeBase(unittest.TestCase):
    def test_worker_init_request_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            async def worker_init_request(self, request):
                await super().worker_init_request(request)

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            import asyncio

            asyncio.run(mock_runtime.worker_init_request(None))

    def test_functions_metadata_request_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                await super().functions_metadata_request(request)

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            import asyncio

            asyncio.run(mock_runtime.functions_metadata_request(None))

    def test_function_load_request_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            async def function_load_request(self, request):
                await super().function_load_request(request)

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            import asyncio

            asyncio.run(mock_runtime.function_load_request(None))

    def test_invocation_request_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            async def invocation_request(self, request):
                await super().invocation_request(request)

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            import asyncio

            asyncio.run(mock_runtime.invocation_request(None))

    def test_function_environment_reload_request_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                await super().function_environment_reload_request(request)

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            import asyncio

            asyncio.run(mock_runtime.function_environment_reload_request(None))

    def test_runtime_implementation(self):
        class TestRuntime(RuntimeBase):
            runtime_name = "test_runtime"
            _invocation_id_cv = contextvars.ContextVar("invocation_id")

            async def worker_init_request(self, request):
                return "worker_init_response"

            async def functions_metadata_request(self, request):
                return "functions_metadata_response"

            async def function_load_request(self, request):
                return "function_load_response"

            async def invocation_request(self, request):
                return "invocation_response"

            async def function_environment_reload_request(self, request):
                return "function_environment_reload_response"

            def start_threadpool_executor(self):
                pass

            def stop_threadpool_executor(self):
                pass

            def get_threadpool_executor(self):
                return None

            @property
            def invocation_id_cv(self):
                return self._invocation_id_cv

        runtime = TestRuntime()
        self.assertEqual(runtime.runtime_name, "test_runtime")

        import asyncio

        self.assertEqual(
            asyncio.run(runtime.worker_init_request(None)), "worker_init_response"
        )
        self.assertEqual(
            asyncio.run(runtime.functions_metadata_request(None)),
            "functions_metadata_response",
        )
        self.assertEqual(
            asyncio.run(runtime.function_load_request(None)), "function_load_response"
        )
        self.assertEqual(
            asyncio.run(runtime.invocation_request(None)), "invocation_response"
        )
        self.assertEqual(
            asyncio.run(runtime.function_environment_reload_request(None)),
            "function_environment_reload_response",
        )

    def test_start_threadpool_executor_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def stop_threadpool_executor(self):
                pass

            def get_threadpool_executor(self):
                pass

            @property
            def invocation_id_cv(self):
                pass

            def start_threadpool_executor(self):
                super().start_threadpool_executor()

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            mock_runtime.start_threadpool_executor()

    def test_stop_threadpool_executor_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def start_threadpool_executor(self):
                pass

            def get_threadpool_executor(self):
                pass

            @property
            def invocation_id_cv(self):
                pass

            def stop_threadpool_executor(self):
                super().stop_threadpool_executor()

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            mock_runtime.stop_threadpool_executor()

    def test_get_threadpool_executor_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def start_threadpool_executor(self):
                pass

            def stop_threadpool_executor(self):
                pass

            @property
            def invocation_id_cv(self):
                pass

            def get_threadpool_executor(self):
                return super().get_threadpool_executor()

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            mock_runtime.get_threadpool_executor()

    def test_invocation_id_cv_property_raises_not_implemented_error(self):
        class MockRuntime(RuntimeBase):
            runtime_name = "mock"

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def start_threadpool_executor(self):
                pass

            def stop_threadpool_executor(self):
                pass

            def get_threadpool_executor(self):
                pass

            @property
            def invocation_id_cv(self):
                return super().invocation_id_cv

        mock_runtime = MockRuntime()

        with self.assertRaises(NotImplementedError):
            _ = mock_runtime.invocation_id_cv

    def test_threadpool_executor_integration(self):
        """Test that threadpool executor methods work correctly when implemented"""
        executor = ThreadPoolExecutor(max_workers=2)

        class TestRuntime(RuntimeBase):
            runtime_name = "test"
            _executor = None

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def start_threadpool_executor(self):
                self._executor = executor

            def stop_threadpool_executor(self):
                if self._executor:
                    self._executor.shutdown(wait=True)
                    self._executor = None

            def get_threadpool_executor(self):
                return self._executor

            @property
            def invocation_id_cv(self):
                return contextvars.ContextVar("test_invocation_id")

        runtime = TestRuntime()
        self.assertIsNone(runtime.get_threadpool_executor())

        runtime.start_threadpool_executor()
        self.assertIsNotNone(runtime.get_threadpool_executor())
        self.assertEqual(runtime.get_threadpool_executor(), executor)

        runtime.stop_threadpool_executor()
        self.assertIsNone(runtime.get_threadpool_executor())

    def test_invocation_id_cv_context_var(self):
        """Test that invocation_id_cv returns a ContextVar"""

        class TestRuntime(RuntimeBase):
            runtime_name = "test"
            _invocation_id_cv = contextvars.ContextVar("invocation_id", default=None)

            async def worker_init_request(self, request):
                pass

            async def functions_metadata_request(self, request):
                pass

            async def function_load_request(self, request):
                pass

            async def invocation_request(self, request):
                pass

            async def function_environment_reload_request(self, request):
                pass

            def start_threadpool_executor(self):
                pass

            def stop_threadpool_executor(self):
                pass

            def get_threadpool_executor(self):
                return None

            @property
            def invocation_id_cv(self):
                return self._invocation_id_cv

        runtime = TestRuntime()
        cv = runtime.invocation_id_cv

        self.assertIsInstance(cv, contextvars.ContextVar)
        self.assertEqual(cv.get(), None)

        cv.set("test-invocation-123")
        self.assertEqual(cv.get(), "test-invocation-123")


class TestRuntimeFeatureChecker(unittest.TestCase):
    def setUp(self):
        # Reset the _module and _runtime_name attributes before each test
        RuntimeTrackerMeta._module = None
        RuntimeTrackerMeta._runtime_name = None

    def test_runtime_not_loaded(self):
        self.assertFalse(RuntimeFeatureChecker.runtime_loaded())
        self.assertIsNone(RuntimeFeatureChecker.get_runtime_name())

    def test_runtime_loaded(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            runtime_name = "fastapi"

        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())
        self.assertEqual(RuntimeFeatureChecker.get_runtime_name(), "fastapi")

    def test_runtime_loaded_without_name(self):
        class TestRuntime(metaclass=RuntimeTrackerMeta):
            pass

        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())
        self.assertIsNone(RuntimeFeatureChecker.get_runtime_name())

    def test_multiple_runtime_checks(self):
        # Initially, no runtime should be loaded
        self.assertFalse(RuntimeFeatureChecker.runtime_loaded())

        class TestRuntime1(metaclass=RuntimeTrackerMeta):
            runtime_name = "runtime1"

        # After defining the first runtime, it should be loaded
        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())
        self.assertEqual(RuntimeFeatureChecker.get_runtime_name(), "runtime1")

        # Define another runtime from the same module
        class TestRuntime2(metaclass=RuntimeTrackerMeta):
            runtime_name = "runtime1"

        # The runtime should still be loaded with the same name
        self.assertTrue(RuntimeFeatureChecker.runtime_loaded())
        self.assertEqual(RuntimeFeatureChecker.get_runtime_name(), "runtime1")
