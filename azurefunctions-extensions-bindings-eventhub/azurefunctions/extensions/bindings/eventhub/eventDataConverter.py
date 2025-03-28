#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import collections.abc
from typing import Any, Optional, get_args, get_origin

from azurefunctions.extensions.base import Datum, InConverter, OutConverter
from .eventData import EventData


class EventDataConverter(
    InConverter,
    OutConverter,
    binding="eventHub",
    trigger="eventHubTrigger",
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        if not issubclass(get_origin(pytype), collections.abc.Iterable):
            return issubclass(pytype, EventData)

        # Extract inner type(s) from iterable
        args = get_args(pytype)
        if not args:
            return False
        
        return any(isinstance(arg, type) and issubclass(arg, EventData) 
                   for arg in args)

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Optional[Any]:
        """
        EventHub allows for batches to be sent. This means the cardinality can be one or many
        When the cardinality is one:
            - The data is of type "model_binding_data" - each event is an independent function invocation
        When the cardinality is many:
            - The data is of type "collection_model_binding_data" - all events are sent in a single function invocation
            - collection_model_binding_data has 1 or more model_binding_data objects
        """
        if data is None or data.type is None or pytype != EventData:
            return None

        # Process each model_binding_data in the collection
        if data.type == "collection_model_binding_data":
            try:
                return [EventData(data=mbd).get_sdk_type() for mbd in data.value.model_binding_data]
            except Exception as e:
                raise ValueError("Failed to decode incoming EventHub batch: " + repr(e)) from e
            
        # Get model_binding_data fields directly
        if data.type == "model_binding_data":
            return EventData(data=data.value).get_sdk_type()
        
        raise ValueError(
            "Unexpected type of data received for the 'eventhub' binding: "
            + repr(data.type)
        )