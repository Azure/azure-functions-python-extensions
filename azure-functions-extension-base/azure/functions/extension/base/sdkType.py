# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import abstractmethod
import sys
from typing import Any, Dict, Optional

if sys.version_info >= (3, 8):
    from typing import TypedDict
    TypedDict = TypedDict[str, Any]
else:
    TypedDict = dict

class SdkType:
    def __init__(self, *, data: Optional[TypedDict] = None):
        self._data = data or {}

    @abstractmethod
    def get_sdk_type(self):
        pass
