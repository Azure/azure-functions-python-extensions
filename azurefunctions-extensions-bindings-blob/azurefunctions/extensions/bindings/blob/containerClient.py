#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json

from azurefunctions.extensions.base import Datum, SdkType
from .utils import (using_system_managed_identity,
                    using_user_managed_identity,
                    validate_connection_setting,
                    get_blob_service_client)


class ContainerClient(SdkType):
    def __init__(self, *, data: Datum) -> None:
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
            self._connection = validate_connection_setting(
                content_json.get("Connection"))
            self._system_managed_identity = using_system_managed_identity(
                self._connection
            )
            self._user_managed_identity = using_user_managed_identity(
                self._connection
            )
            self._containerName = content_json.get("ContainerName")
            self._blobName = content_json.get("BlobName")

    # Returns a ContainerClient
    def get_sdk_type(self):
        if self._data:
            blob_service_client = get_blob_service_client(self._system_managed_identity,
                                                          self._user_managed_identity,
                                                          self._connection)
            return blob_service_client.get_container_client(
                container=self._containerName
            )
        else:
            raise ValueError(f"Unable to create {self.__class__.__name__} SDK type.")
