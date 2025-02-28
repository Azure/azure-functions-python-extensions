#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import re
from typing import Union
import uamqp

from azure.eventhub import EventData
from azurefunctions.extensions.base import Datum, SdkType


class EventHubData(SdkType):
    def __init__(self, *, data: Union[bytes, Datum]) -> None:
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
            self.decoded_message = self.__get_eventhub_content(self._content)
    
    def __get_eventhub_content(self, content):
        if content:
            return uamqp.Message().decode_from_bytes(content)
        else:
            return None

    def get_sdk_type(self):
        # https://github.com/Azure/azure-sdk-for-python/issues/39711
        if self.decoded_message:
            return EventData._from_message(self.decoded_message)
        else:
            return None
