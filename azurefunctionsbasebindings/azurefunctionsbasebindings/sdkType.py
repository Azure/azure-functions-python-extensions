# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import abstractmethod
from typing import Any, Optional


class SdkType():
    def __init__(self, *, data: Optional[dict[str, Any]] = None):
        self._data = data or {}

    @abstractmethod
    def get_sdk_type(self):
        pass
