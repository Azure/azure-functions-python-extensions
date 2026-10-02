#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.connectors.office365 import (
    GraphClientReceiveMessage as AzureGraphClientReceiveMessage
)
from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_graph_client_receive_messages


class GraphClientReceiveMessage(
    ConnectorSdkType[list[AzureGraphClientReceiveMessage]],
    AzureGraphClientReceiveMessage,
):
    """Azure Functions binding for Microsoft Graph email messages."""

    _deserialize = staticmethod(deserialize_graph_client_receive_messages)
