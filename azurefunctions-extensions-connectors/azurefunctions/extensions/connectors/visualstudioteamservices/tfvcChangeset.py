#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Azure DevOps TFVC changesets using the generated SDK item model."""

from azure.connectors.visualstudioteamservices import (
    TfvcChangeset as AzureTfvcChangeset,
)

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_changesets


class TfvcChangeset(ConnectorSdkType[list[AzureTfvcChangeset]], AzureTfvcChangeset):
    """Return SDK TFVC changeset items for OnTfvcCheckIn polling callbacks."""

    _deserialize = staticmethod(deserialize_changesets)
