# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import abstractmethod
import sys
from typing import Any, Dict, Optional

if sys.version_info < (3, 9):
    from typing import TypedDict as PyTypedDict
else:
    PyTypedDict = dict

class TypedDict(PyTypedDict):
    pass
    
class SdkType:
    def __init__(self, *, data: Optional[TypedDict[str, Any]] = None):
        self._data = data or {}

    @abstractmethod
    def get_sdk_type(self):
        pass
