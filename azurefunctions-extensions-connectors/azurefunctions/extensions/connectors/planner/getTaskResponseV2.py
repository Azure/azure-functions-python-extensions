#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Planner trigger tasks using the generated SDK item model."""

from azure.connectors.planner import GetTaskResponseV2 as AzureGetTaskResponseV2

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_tasks


class GetTaskResponseV2(
    ConnectorSdkType[list[AzureGetTaskResponseV2]], AzureGetTaskResponseV2,
):
    """Return Planner SDK tasks with typed categories and raw assignment entries."""

    _deserialize = staticmethod(deserialize_tasks)
