#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Azure DevOps build callbacks using the generated SDK item model."""

from azure.connectors.visualstudioteamservices import BuildResult as AzureBuildResult

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_builds


class BuildResult(ConnectorSdkType[list[AzureBuildResult]], AzureBuildResult):
    """Return SDK build items for OnBuildCompleted polling callbacks."""

    _deserialize = staticmethod(deserialize_builds)
