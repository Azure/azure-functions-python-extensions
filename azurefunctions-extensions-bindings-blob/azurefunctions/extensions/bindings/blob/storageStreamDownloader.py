#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
from typing import Union

from azure.storage.blob import BlobServiceClient
from azurefunctions.extensions.base import Datum, SdkType
from .utils import get_connection_string, using_managed_identity


class StorageStreamDownloader(SdkType):
    def __init__(self, *, data: Union[bytes, Datum]) -> None:
        # model_binding_data properties
        self._data = data
        self._using_managed_identity = False
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
            self._connection = get_connection_string(content_json["Connection"])
            self._using_managed_identity = using_managed_identity(
                content_json["Connection"]
            )
            self._containerName = content_json["ContainerName"]
            self._blobName = content_json["BlobName"]

    # Returns a StorageStreamDownloader
    def get_sdk_type(self):
        if self._data:
            if self._using_managed_identity:
                blob_service_client = BlobServiceClient(account_url=self._connection)
            else:
                blob_service_client = BlobServiceClient.from_connection_string(
                    self._connection
                )
            # download_blob() returns a StorageStreamDownloader object
            return blob_service_client.get_blob_client(
                container=self._containerName,
                blob=self._blobName,
            ).download_blob()
        else:
            return None
