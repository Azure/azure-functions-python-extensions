#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json

from azurefunctions.extensions.base import Datum, SdkType
from .utils import (using_system_managed_identity,
                    using_user_managed_identity,
                    get_blob_service_client)


class BlobClient(SdkType):
    def __init__(self, *, data: Datum) -> None:
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
            self._connection = content_json.get("Connection")
            self._system_managed_identity = using_system_managed_identity(
                self._connection
            )
            self._user_managed_identity = using_user_managed_identity(
                self._connection
            )
            self._containerName = content_json.get("ContainerName")
            self._blobName = content_json.get("BlobName")

    def get_sdk_type(self):
        """
        When using Managed Identity, the only way to create a BlobClient is
        through a BlobServiceClient. There are two ways to create a
        BlobServiceClient:
        1. Through the constructor: this is the only option when using Managed Identity
            1a. If system-based MI, the credential is DefaultAzureCredential
            1b. If user-based MI, the credential is ManagedIdentityCredential
        2. Through from_connection_string: this is the only option when
        not using Managed Identity

        We track if Managed Identity is being used through a flag.
        """
        if self._data:
            blob_service_client = get_blob_service_client(self._system_managed_identity,
                                                          self._user_managed_identity,
                                                          self._connection)
            return blob_service_client.get_blob_client(
                container=self._containerName,
                blob=self._blobName,
            )
        else:
            raise ValueError(f"Unable to create {self.__class__.__name__} SDK type.")
