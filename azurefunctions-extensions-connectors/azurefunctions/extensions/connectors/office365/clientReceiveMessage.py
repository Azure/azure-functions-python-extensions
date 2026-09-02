#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.connectors.office365 import ClientReceiveMessage as AzureClientReceiveMessage
from .._sdk_type import ConnectorSdkType
from ._deserialization import deserialize_client_receive_messages


class ClientReceiveMessage(
    ConnectorSdkType[list[AzureClientReceiveMessage]],
    AzureClientReceiveMessage,
):
    """Azure Functions binding for legacy Office 365 email messages."""

    _deserialize = staticmethod(deserialize_client_receive_messages)
