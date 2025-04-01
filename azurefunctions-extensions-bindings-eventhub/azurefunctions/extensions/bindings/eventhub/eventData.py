#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Optional
import uamqp

from azure.eventhub import EventData
from azurefunctions.extensions.base import Datum, SdkType


class EventData(SdkType):
    def __init__(self, *, data: Datum) -> None:
        # model_binding_data properties
        self._data = data
        self._version = None
        self._source = None
        self._content_type = None
        self._content = None
        self.decoded_message = None
        if self._data:
            self._version = data.version
            self._source = data.source
            self._content_type = data.content_type
            self._content = data.content
            self.decoded_message = self._get_eventhub_content(self._content)
    
    def _get_eventhub_content(self, content):
        """
        When receiving the EventBindingData, the content field is in the form of bytes.
        This content must be decoded in order to construct an EventData object from the azure.eventhub SDK.
        The .NET worker uses the Azure.Core.Amqp library to do this:
        https://github.com/Azure/azure-functions-dotnet-worker/blob/main/extensions/Worker.Extensions.EventHubs/src/EventDataConverter.cs#L45
        """
        if content:
            try:
                return uamqp.Message().decode_from_bytes(content)
            except Exception as e:
                raise ValueError(f"Failed to decode EventHub content: {e}") from e
            
        return None

    def get_sdk_type(self) -> Optional[EventData]:
        """
        When receiving an EventHub message, the content portion after being decoded
        is used in the constructor to create an EventData object. This will contain
        fields such as message, enqueued_time, and more.
        """
        # https://github.com/Azure/azure-sdk-for-python/issues/39711
        if self.decoded_message:
            return EventData._from_message(self.decoded_message)
        
        return None
