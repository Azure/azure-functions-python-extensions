#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
from typing import Union

from azure.storage.blob import BlobClient as BlobClientSdk
from azurefunctions.extensions.base import Datum, SdkType
from .utils import ConnectionConfig


class BlobClient(SdkType):
    def __init__(self, *, data: Union[bytes, Datum]) -> None:
        # model_binding_data properties
        self._data = data
        self._version = None
        self._source = None
        self._content_type = None
        self._connection = None
        self._containerName = None
        self._blobName = None
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

    # Returns a BlobClient
    def get_sdk_type(self):
        if self._data:
            return BlobClientSdk.from_connection_string(
                conn_str=self._connection,
                container_name=self._containerName,
                blob_name=self._blobName,
            )
        else:
            return None
