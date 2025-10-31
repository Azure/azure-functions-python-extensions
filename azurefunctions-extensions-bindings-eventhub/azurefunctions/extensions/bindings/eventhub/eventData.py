#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Optional

from azure.eventhub import EventData as EventDataSDK
from azurefunctions.extensions.base import Datum, SdkType


class EventData(SdkType, EventDataSDK):
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

    def get_sdk_type(self) -> Optional[EventDataSDK]:
        """
        When receiving an EventHub message, the content portion after being decoded
        is used in the constructor to create an EventData object. This will contain
        fields such as message, enqueued_time, and more.
        """
        if self._content:
            return EventDataSDK.from_bytes(self._content)
        else:
            raise ValueError(f"Unable to create {self.__class__.__name__} SDK type.")
