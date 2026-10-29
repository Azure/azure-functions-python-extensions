#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Bind Teams membership changes using the SDK's dictionary item contract."""

from typing import Any

from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_membership_changes


class OnGroupMemberChangeResponse(ConnectorSdkType[list[dict[str, Any]]]):
    """Return raw member dictionaries without inventing a fixed SDK item model."""

    _deserialize = staticmethod(deserialize_membership_changes)
