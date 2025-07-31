#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azure.servicebus import ServiceBusReceivedMessage as ServiceBusReceivedMessageSdk
from azurefunctions.extensions.base import Datum, SdkType
from .utils import get_decoded_message


class ServiceBusReceivedMessage(SdkType, ServiceBusReceivedMessageSdk):
    def __init__(self, *, data: Datum) -> None:
        # model_binding_data properties
        self._data = data
        self._version = None
        self._source = None
        self._content_type = None
        self._content = None
        self._decoded_message = None
        if self._data:
            self._version = data.version
            self._source = data.source
            self._content_type = data.content_type
            self._content = data.content
            self._decoded_message = get_decoded_message(self._content)

    def get_sdk_type(self):
        """
        Returns a ServiceBusReceivedMessage.
        Message settling is not yet supported.
        """
        if self._decoded_message:
            return ServiceBusReceivedMessageSdk(self._decoded_message, receiver=None)
        else:
            return None
