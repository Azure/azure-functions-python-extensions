#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Azure DevOps Git pushes using the generated SDK item model."""

from azure.connectors.visualstudioteamservices import GitPush as AzureGitPush

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_pushes


class GitPush(ConnectorSdkType[list[AzureGitPush]], AzureGitPush):
    """Return SDK Git push items for OnGitPush polling callbacks."""

    _deserialize = staticmethod(deserialize_pushes)
