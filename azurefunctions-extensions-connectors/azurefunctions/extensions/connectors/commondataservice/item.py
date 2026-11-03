#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind legacy CDS polling records using the generated SDK item model."""

from azure.connectors.commondataservice import Item as AzureItem

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_items


class Item(ConnectorSdkType[list[AzureItem]], AzureItem):
    """Return legacy polling items with raw JSON in dynamic_properties."""

    _deserialize = staticmethod(deserialize_items)
