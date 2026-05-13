# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import abstractmethod


class SdkType:
    def __init__(self, *, data: dict = None):
        self._data = data or {}

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """Returns whether this SDK type supports deferred binding.

        Override this method in subclasses to return False if the extension
        should not use deferred binding (SupportsDeferredBinding flag = False).

        Returns:
            True by default. Override to return False to disable deferred binding.
        """
        return True

    @abstractmethod
    def get_sdk_type(self):
        pass
