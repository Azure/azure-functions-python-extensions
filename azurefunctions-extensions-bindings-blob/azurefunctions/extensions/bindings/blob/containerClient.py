#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
from typing import Union

from azure.storage.blob import ContainerClient as ContainerClientSdk
from azurefunctions.extensions.base import Datum, SdkType
from .utils import ConnectionConfig


class ContainerClient(SdkType):
    def __init__(self, *, data: Union[bytes, Datum]) -> None:
        # model_binding_data properties
        self._data = data
        self._version = ""
        self._source = ""
        self._content_type = ""
        self._connection = ""
        self._containerName = ""
        self._blobName = ""
        if self._data:
            self._version = data.version
            self._source = data.source
            self._content_type = data.content_type
            content_json = json.loads(data.content)
            self._connection = ConnectionConfig(
                connection_string=content_json["Connection"]
            )
            self._containerName = content_json["ContainerName"]
            self._blobName = content_json["BlobName"]

    # Returns a ContainerClient
    def get_sdk_type(self):
        if self._data:
            return ContainerClientSdk.from_connection_string(
                conn_str=self._connection, container_name=self._containerName
            )
        else:
            return None
