#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Dataflows refresh callbacks using the generated SDK refresh model."""

from azure.connectors.dataflows import RefreshModel as AzureRefreshModel

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_refreshes


class RefreshModel(ConnectorSdkType[list[AzureRefreshModel]], AzureRefreshModel):
    """Return SDK refresh items for OnRefreshComplete polling callbacks."""

    _deserialize = staticmethod(deserialize_refreshes)
