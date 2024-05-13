#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import os
from typing import Union

from azure.storage.blob import BlobServiceClient
from azurefunctions.extensions.base import Datum, SdkType


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
            self._using_managed_identity = using_managed_identity(
                content_json["Connection"]
            )
            self._connection = validate_connection_string(content_json["Connection"])
            self._containerName = content_json["ContainerName"]
            self._blobName = content_json["BlobName"]

    # Returns a ContainerClient
    def get_sdk_type(self):
        if self._data:
            if self._using_managed_identity:
                blob_service_client = BlobServiceClient(account_url=self._connection)
                return blob_service_client.get_container_client(
                    container=self._containerName
                )
            else:
                blob_service_client = BlobServiceClient.from_connection_string(
                    self._connection
                )
                return blob_service_client.get_container_client(
                    container=self._containerName
                )
        else:
            return None


def using_managed_identity(connection_name: str) -> bool:
    return (os.getenv(connection_name + "__serviceUri") is not None) or (
        os.getenv(connection_name + "__blobServiceUri") is not None
    )


def validate_connection_string(connection_string: str) -> str:
    """
    Validates the connection string. If the connection string is
    not an App Setting, an error will be thrown.
    """
    if not os.getenv(connection_string):
        raise ValueError(
            f"Storage account connection string {connection_string} does not exist. "
            f"Please make sure that it is a defined App Setting."
        )
    return os.getenv(connection_string)
