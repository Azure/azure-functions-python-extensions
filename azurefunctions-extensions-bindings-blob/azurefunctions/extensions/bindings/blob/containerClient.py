#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
from typing import Union

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azurefunctions.extensions.base import Datum, SdkType
from .utils import get_connection_string, using_managed_identity


class ContainerClient(SdkType):
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
            self._connection = get_connection_string(content_json.get("Connection"))
            self._using_managed_identity = using_managed_identity(
                content_json.get("Connection")
            )
            self._containerName = content_json.get("ContainerName")
            self._blobName = content_json.get("BlobName")

    # Returns a ContainerClient
    def get_sdk_type(self):
        if self._data:
            blob_service_client = (
                BlobServiceClient(
                    account_url=self._connection, credential=DefaultAzureCredential()
                )
                if self._using_managed_identity
                else BlobServiceClient.from_connection_string(self._connection)
            )
            return blob_service_client.get_container_client(
                container=self._containerName
            )
        else:
            return None
