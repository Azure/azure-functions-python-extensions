#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind SharePoint item and file deletion trigger metadata."""

from azure.connectors.sharepointonline import DeletedItem as AzureDeletedItem

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_deleted_items


class DeletedItem(ConnectorSdkType[list[AzureDeletedItem]], AzureDeletedItem):
    """Bind deleted items as a list of generated SDK models."""

    _deserialize = staticmethod(deserialize_deleted_items)
