# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""
Runtime Base Classes and Metaclass Registration

This module provides the core abstractions for runtime packages:
- RuntimeTrackerMeta: Metaclass that auto-registers runtimes at import time
- RuntimeBase: Abstract base class that all runtimes must extend
- RuntimeFeatureChecker: Utility to check if a runtime is loaded
- VersionNamespace: Helper for exposing VERSION in the expected format

This module should be packaged as azurefunctions.extensions.base
"""

import contextvars
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

base_runtime_module = __name__


class RuntimeTrackerMeta(type):
    """
    Metaclass that automatically registers runtime implementations.

    When a runtime class is defined with this metaclass, it automatically
    registers its module name. This allows the proxy worker to discover
    which runtime is loaded without explicit registration.

    Similar to ModuleTrackerMeta in azurefunctions.extensions.base
    """
    _module = None
    _runtime_name = None
    _package_name = None

    def __new__(cls, name, bases, dct, **kwargs):
        new_class = super().__new__(cls, name, bases, dct)
        new_module = dct.get("__module__")
        runtime_name = dct.get("runtime_name")

        # Only register if this is not the base module itself
        if new_module != base_runtime_module:
            if cls._module is None:
                cls._module = new_module
                cls._runtime_name = runtime_name
                if '.runtime' in new_module:
                    cls._package_name = new_module.rsplit('.runtime', 1)[0]
                else:
                    cls._package_name = new_module.split('.')[0]
            elif cls._module != new_module:
                raise Exception(
                    f"Only one runtime package shall be imported at a time. "
                    f"{cls._module} and {new_module} are imported."
                )

        return new_class

    @classmethod
    def get_module(cls):
        """Get the registered runtime module name"""
        return cls._module

    @classmethod
    def get_runtime_name(cls):
        """Get the registered runtime name"""
        return cls._runtime_name

    @classmethod
    def get_package_name(cls):
        """Get the runtime package name (without .runtime suffix)"""
        return cls._package_name

    @classmethod
    def module_imported(cls):
        """Check if a runtime module has been imported"""
        return cls._module is not None


class RuntimeBase(metaclass=RuntimeTrackerMeta):
    """
    Abstract base class for all runtime implementations.

    Runtime packages (FastAPI, Flask, etc.) must:
    1. Import this base class
    2. Create a subclass with runtime_name defined
    3. Implement all required event handler methods
    4. Expose VERSION via a 'version' namespace in the package __init__.py

    Example runtime package structure:
        # azure_functions_fastapi/runtime.py
        from azurefunctions.extensions.base import RuntimeBase

        class Runtime(RuntimeBase):
            runtime_name = "fastapi"

            @property
            def VERSION(self):
                from . import VERSION
                return VERSION

            async def worker_init_request(self, request):
                # Implementation
                pass

            # ... other methods

        # azure_functions_fastapi/__init__.py
        from azurefunctions.extensions.base import VersionNamespace
        from .runtime import Runtime

        VERSION = "1.0.0"
        version = VersionNamespace(VERSION)  # For _library_worker.version.VERSION

        # Export public API
        __all__ = ['Runtime', 'VERSION', 'version', ...]
    """

    # Runtime identification (must be set by subclass)
    runtime_name = None

    @property
    @abstractmethod
    def VERSION(self) -> str:
        """
        Get the runtime version string.

        This version is logged during worker initialization and environment
        reload for debugging and diagnostics purposes. It should match the
        version in the runtime package's version.py file.

        The runtime package must also expose this as _library_worker.version.VERSION
        for compatibility with the proxy worker's logging. Use VersionNamespace
        helper class in the package's __init__.py.

        Returns:
            Version string (e.g., "1.0.0")
        """
        raise NotImplementedError()

    @abstractmethod
    async def worker_init_request(self, request):
        """
        Handle WorkerInitRequest - Initialize the runtime

        Args:
            request: WorkerInitRequest protobuf message

        Returns:
            WorkerInitResponse protobuf message
        """
        raise NotImplementedError()

    @abstractmethod
    async def functions_metadata_request(self, request):
        """
        Handle FunctionMetadataRequest - Return function metadata

        Args:
            request: FunctionMetadataRequest protobuf message

        Returns:
            FunctionMetadataResponse protobuf message
        """
        raise NotImplementedError()

    @abstractmethod
    async def function_load_request(self, request):
        """
        Handle FunctionLoadRequest - Load a specific function

        Args:
            request: FunctionLoadRequest protobuf message

        Returns:
            FunctionLoadResponse protobuf message
        """
        raise NotImplementedError()

    @abstractmethod
    async def invocation_request(self, request):
        """
        Handle InvocationRequest - Execute a function invocation

        Args:
            request: InvocationRequest protobuf message

        Returns:
            InvocationResponse protobuf message
        """
        raise NotImplementedError()

    @abstractmethod
    async def function_environment_reload_request(self, request):
        """
        Handle FunctionEnvironmentReloadRequest - Reload the environment

        Args:
            request: FunctionEnvironmentReloadRequest protobuf message

        Returns:
            FunctionEnvironmentReloadResponse protobuf message
        """
        raise NotImplementedError()

    @abstractmethod
    def start_threadpool_executor(self):
        """
        Initialize and start the threadpool executor.

        This is called during worker initialization to set up the thread pool
        for executing synchronous functions. The implementation should respect
        PYTHON_THREADPOOL_THREAD_COUNT setting if applicable.

        For async-only runtimes, this can be a no-op.
        """
        raise NotImplementedError()

    @abstractmethod
    def stop_threadpool_executor(self):
        """
        Stop and cleanup the threadpool executor.

        This is called during worker shutdown to gracefully terminate the
        thread pool. The implementation should wait for pending tasks to
        complete.

        For async-only runtimes, this can be a no-op.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_threadpool_executor(self) -> Optional[ThreadPoolExecutor]:
        """
        Get the current threadpool executor instance.

        Returns:
            ThreadPoolExecutor instance if available, None otherwise.
            For async-only runtimes, this should return None.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def invocation_id_cv(self) -> contextvars.ContextVar:
        """
        Get the invocation ID context variable.

        This ContextVar is used to track the current invocation ID across
        different execution contexts (threads, async tasks). It's essential
        for correlating logs and telemetry with specific function invocations.

        Returns:
            ContextVar for storing invocation IDs
        """
        raise NotImplementedError()


class VersionNamespace:
    """
    Helper class to create a version namespace for runtime packages.

    The dispatcher accesses _library_worker.version.VERSION, so runtime
    packages must expose a 'version' attribute with a 'VERSION' attribute.

    Usage in runtime package's __init__.py:
        from azurefunctions.extensions.base import VersionNamespace

        VERSION = "1.0.0"
        version = VersionNamespace(VERSION)
    """
    def __init__(self, version_string: str):
        self.VERSION = version_string


class RuntimeFeatureChecker:
    """
    Utility class to check if a runtime has been loaded.

    Similar to HttpV2FeatureChecker in azurefunctions.extensions.base
    """

    @staticmethod
    def runtime_loaded():
        """Check if a runtime has been imported and registered"""
        return RuntimeTrackerMeta.module_imported()

    @staticmethod
    def get_runtime_name():
        """Get the name of the loaded runtime"""
        return RuntimeTrackerMeta.get_runtime_name()
