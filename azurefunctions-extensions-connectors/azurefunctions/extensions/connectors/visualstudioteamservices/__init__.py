#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""SDK item bindings for Azure DevOps (VSTS) connector polling triggers."""

from ..connectorConverter import ConnectorConverter

try:
    from .buildResult import BuildResult
    from .gitPullRequest import GitPullRequest
    from .gitPush import GitPush
    from .tfvcChangeset import TfvcChangeset
    from .triggerWorkItemResponse import TriggerWorkItemResponse
except ModuleNotFoundError as error:
    if error.name != "azure.connectors.visualstudioteamservices":
        raise
    raise ImportError(
        "Azure DevOps bindings require an azure-connectors build containing "
        "azure.connectors.visualstudioteamservices. Install SDK main revision "
        "5e93a98c11a9eec43c4d3bbf441333b80d9ac7cb or a later build with that "
        "module; the published 0.5.0b1 package does not contain it."
    ) from error

__all__ = [
    "ConnectorConverter",
    "BuildResult",
    "GitPullRequest",
    "GitPush",
    "TfvcChangeset",
    "TriggerWorkItemResponse",
]
