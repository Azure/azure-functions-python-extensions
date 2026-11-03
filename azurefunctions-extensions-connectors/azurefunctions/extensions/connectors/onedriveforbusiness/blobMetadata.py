#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind OneDrive for Business file-property trigger items."""

from azure.connectors.onedriveforbusiness import BlobMetadata as AzureBlobMetadata

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_blob_metadata


class BlobMetadata(ConnectorSdkType[list[AzureBlobMetadata]], AzureBlobMetadata):
    """Bind file properties as a list of generated OneDrive SDK models."""

    _deserialize = staticmethod(deserialize_blob_metadata)
