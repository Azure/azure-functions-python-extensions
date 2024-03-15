# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from abc import abstractmethod
import sys
from typing import Any, Dict, Optional

class SdkType:
    def __init__(self, *, data: dict = None):
        self._data = data or {}

    @abstractmethod
    def get_sdk_type(self):
        pass
