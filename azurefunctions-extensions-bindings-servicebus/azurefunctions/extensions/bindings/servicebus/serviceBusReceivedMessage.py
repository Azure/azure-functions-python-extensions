#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.servicebus import ServiceBusReceivedMessage as ServiceBusReceivedMessageSdk
from azurefunctions.extensions.base import Datum, SdkType


_LOCK_TOKEN_LENGTH = 16


class ServiceBusReceivedMessage(SdkType, ServiceBusReceivedMessageSdk):
    def __init__(self, *, data: Datum) -> None:
        # model_binding_data properties
        self._data = data
        self._version = None
        self._source = None
        self._content_type = None
        self._content = None
        if self._data:
            self._version = data.version
            self._source = data.source
            self._content_type = data.content_type
            self._content = data.content

    def get_sdk_type(self):
        """
        Returns a receiver-less ServiceBusReceivedMessage containing the
        message content and broker metadata.
        """
        if self._content:
            return ServiceBusReceivedMessageSdk.from_bytes(
                self._content[_LOCK_TOKEN_LENGTH:]
            )
        else:
            return None
