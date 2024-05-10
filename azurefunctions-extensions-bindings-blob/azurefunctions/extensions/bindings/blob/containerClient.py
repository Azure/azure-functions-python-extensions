#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import os
from typing import Union

from azure.storage.blob import ContainerClient as ContainerClientSdk
from azurefunctions.extensions.base import Datum, SdkType


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
            self._connection = content_json["Connection"]
            self._containerName = content_json["ContainerName"]
            self._blobName = content_json["BlobName"]

    def validate_connection_string(self):
        """
        Validates the connection string. If the connection string is
        not an App Setting, an error will be thrown.
        """
        if not os.getenv(self._connection):
            raise ValueError(
                f"Storage account connection string {self._connection} does not exist. "
                f"Please make sure that it is a defined App Setting."
            )
        self._connection = os.getenv(self._connection)

    # Returns a ContainerClient
    def get_sdk_type(self):
        ContainerClient.validate_connection_string(self)
        if self._data:
            return ContainerClientSdk.from_connection_string(
                conn_str=self._connection, container_name=self._containerName
            )
        else:
            return None
