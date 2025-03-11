#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Any, Optional

from azurefunctions.extensions.base import Datum, InConverter, OutConverter

from .eventHubData import EventHubData


class EventHubDataConverter(
    InConverter,
    OutConverter,
    binding="eventHub",
    trigger="eventHubTrigger",
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        return issubclass(
            pytype, (EventHubData)
        )

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Optional[Any]:
        if data is None or data.type is None:
            return None

        if data.type != "model_binding_data":
            raise ValueError(
                 "Unexpected type of data received for the 'eventhub' binding: "
                + repr(data.type)
            )
        
        content = data.value

        # Determines which sdk type to return based on pytype
        if pytype == EventHubData:
            return EventHubData(data=content).get_sdk_type()
        
        return None
