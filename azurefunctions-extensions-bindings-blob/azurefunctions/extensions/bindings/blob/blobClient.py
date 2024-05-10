#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json
import os
from typing import Union

from azure.storage.blob import BlobServiceClient
from azurefunctions.extensions.base import Datum, SdkType


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
            self._using_managed_identity = using_managed_identity(
                content_json["Connection"]
            )
            self._connection = validate_connection_string(content_json["Connection"])
            self._containerName = content_json["ContainerName"]
            self._blobName = content_json["BlobName"]

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
            if self._using_managed_identity:
                blob_service_client = BlobServiceClient(account_url=self._connection)
                return blob_service_client.get_blob_client(
                    container=self._containerName,
                    blob=self._blobName,
                )
            else:
                blob_service_client = BlobServiceClient.from_connection_string(
                    self._connection
                )
                return blob_service_client.get_blob_client(
                    container=self._containerName,
                    blob=self._blobName,
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

    When using managed identity, the connection string variable name is formatted like so:
    Input: <CONNECTION_NAME_PREFIX>__serviceUri
    Trigger: <CONNECTION_NAME_PREFIX>__blobServiceUri
    The variable received will be <CONNECTION_NAME_PREFIX>. Therefore, we need to append
    the suffix to obtain the storage URI and create the client.

    If managed identity is being used, we set the using_managed_identity property to True.

    There are four cases:
    1. Not using managed identity: the environment variable exists as is
    2. Using managed identity for blob input: __serviceUri must be appended
    3. Using managed identity for blob trigger: __blobServiceUri must be appended
    4. None of these cases existed, so the connection variable is invalid.
    """
    if os.getenv(connection_string):
        return os.getenv(connection_string)
    elif os.getenv(connection_string + "__serviceUri"):
        return os.getenv(connection_string + "__serviceUri")
    elif os.getenv(connection_string + "__blobServiceUri"):
        return os.getenv(connection_string + "__blobServiceUri")
    else:
        raise ValueError(
            f"Storage account connection string {connection_string} does not exist. "
            f"Please make sure that it is a defined App Setting."
        )
