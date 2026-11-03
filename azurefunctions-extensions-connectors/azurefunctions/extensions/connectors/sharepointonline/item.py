#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind SharePoint list and file-property trigger items."""

from azure.connectors.sharepointonline import Item as AzureItem

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_items


class Item(ConnectorSdkType[list[AzureItem]], AzureItem):
    """Bind SDK items with raw JSON columns in dynamic_properties."""

    _deserialize = staticmethod(deserialize_items)
