#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Azure DevOps work-item callbacks without losing custom fields."""

from azure.connectors.visualstudioteamservices import (
    TriggerWorkItemResponse as AzureTriggerWorkItemResponse,
)

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_work_items


class TriggerWorkItemResponse(
    ConnectorSdkType[list[AzureTriggerWorkItemResponse]], AzureTriggerWorkItemResponse,
):
    """Return SDK work-item records with raw JSON dictionaries in fields."""

    _deserialize = staticmethod(deserialize_work_items)
