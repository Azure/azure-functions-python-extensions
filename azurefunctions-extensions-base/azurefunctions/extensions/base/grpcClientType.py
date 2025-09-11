# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class GrpcClientType:
    def __init__(self, *, data: dict = None):
        self._data = data or {}
