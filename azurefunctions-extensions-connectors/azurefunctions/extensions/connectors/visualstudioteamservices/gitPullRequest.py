#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Azure DevOps pull requests using the generated SDK item model."""

from azure.connectors.visualstudioteamservices import (
    GitPullRequest as AzureGitPullRequest,
)

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_pull_requests


class GitPullRequest(ConnectorSdkType[list[AzureGitPullRequest]], AzureGitPullRequest):
    """Return SDK items for pull-request-created and closed polling callbacks."""

    _deserialize = staticmethod(deserialize_pull_requests)
