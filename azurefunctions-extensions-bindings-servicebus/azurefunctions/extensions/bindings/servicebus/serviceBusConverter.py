#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import collections.abc
from typing import Any, get_args, get_origin

from azurefunctions.extensions.base import Datum, InConverter
from .serviceBusReceivedMessage import ServiceBusReceivedMessage


class ServiceBusConverter(
    InConverter,
    binding='serviceBusTrigger', trigger=True
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        if pytype is None:
            return False
        
        # The annotation is a class/type (not an object) - not iterable
        if (isinstance(pytype, type)
                and issubclass(pytype, ServiceBusReceivedMessage)):
            return True
        
        # An iterable who only has one inner type and is a subclass of SdkType
        return cls._is_iterable_supported_type(pytype)

    @classmethod
    def _is_iterable_supported_type(cls, annotation: type) -> bool:
        # Check base type from type hint. Ex: List from List[SdkType]
        base_type = get_origin(annotation)
        if (base_type is None
                or not issubclass(base_type, collections.abc.Iterable)):
            return False

        inner_types = get_args(annotation)
        if inner_types is None or len(inner_types) != 1:
            return False
        
        inner_type = inner_types[0]

        return (isinstance(inner_type, type) 
                and issubclass(inner_type, ServiceBusReceivedMessage))

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Any:
        """
        ServiceBus allows for batches to be sent. This means the cardinality can be one or many.
        When the cardinality is one:
            - The data is of type "model_binding_data" - each event is an independent function invocation
        When the cardinality is many:
            - The data is of type "collection_model_binding_data" - all events are sent in a single function invocation
            - collection_model_binding_data has 1 or more model_binding_data objects
        """
        if data is None or data.type is None or pytype != ServiceBusReceivedMessage:
            return None

        data_type = data.type

        if data_type == "model_binding_data":
            return ServiceBusReceivedMessage(data=data.value).get_sdk_type()
        elif data_type == "collection_model_binding_data":
            try:
                return [ServiceBusReceivedMessage(data=mbd).get_sdk_type() for mbd in data.value.model_binding_data]
            except Exception as e:
                raise ValueError("Failed to decode incoming ServiceBus batch: " + repr(e)) from e
        else:
            raise ValueError(
                f'unexpected type of data received for the "servicebus" binding '
                f": {data_type!r}"
            )
