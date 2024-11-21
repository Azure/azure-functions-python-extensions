#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
from typing import Union

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azurefunctions.extensions.base import Datum, SdkType
from .utils import get_connection_string, using_managed_identity


class BlobClient(SdkType):
    def __init__(self, *, data: Union[bytes, Datum]) -> None:
        # model_binding_data properties
        self._data = data
        self._using_managed_identity = False
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
            self._connection = get_connection_string(content_json.get("Connection"))
            self._using_managed_identity = using_managed_identity(
                content_json.get("Connection")
            )
            self._containerName = content_json.get("ContainerName")
            self._blobName = content_json.get("BlobName")

    def get_sdk_type(self):
        """
        When using Managed Identity, the only way to create a BlobClient is
        through a BlobServiceClient. There are two ways to create a
        BlobServiceClient:
        1. Through the constructor: this is the only option when using Managed Identity
        2. Through from_connection_string: this is the only option when not using Managed Identity

        We track if Managed Identity is being used through a flag.
        """
        if self._data:
            blob_service_client = (
                BlobServiceClient(
                    account_url=self._connection, credential=DefaultAzureCredential()
                )
                if self._using_managed_identity
                else BlobServiceClient.from_connection_string(self._connection)
            )
            return blob_service_client.get_blob_client(
                container=self._containerName,
                blob=self._blobName,
            )
        else:
            return None
