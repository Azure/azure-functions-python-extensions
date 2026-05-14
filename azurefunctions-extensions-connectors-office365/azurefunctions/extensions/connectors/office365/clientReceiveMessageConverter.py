#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import collections.abc
from typing import Any, Optional, get_args, get_origin

from azurefunctions.extensions.base import Datum, InConverter
from .clientReceiveMessage import ClientReceiveMessage


class ClientReceiveMessageConverter(
    InConverter,
    binding='connectorTrigger', trigger=True
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        if pytype is None:
            return False

        # The annotation is a class/type (not an object) - not iterable
        if (isinstance(pytype, type)
                and issubclass(pytype, ClientReceiveMessage)):
            return True

        # An iterable who only has one inner type and is a subclass of ClientReceiveMessage
        return cls._is_iterable_supported_type(pytype)

    @classmethod
    def _is_iterable_supported_type(cls, annotation: type) -> bool:
        # Check base type from type hint. Ex: List from List[ClientReceiveMessage]
        base_type = get_origin(annotation)
        if (base_type is None
                or not issubclass(base_type, collections.abc.Iterable)):
            return False

        inner_types = get_args(annotation)
        if inner_types is None or len(inner_types) != 1:
            return False

        inner_type = inner_types[0]

        return (isinstance(inner_type, type)
                and issubclass(inner_type, ClientReceiveMessage))

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Optional[Any]:
        """
        Office365 Connector allows for batches. This means the cardinality can be one or many.
        When the cardinality is one:
            - The data is of type "model_binding_data" - each message is an independent
              function invocation
            - Return a single ClientReceiveMessage object
        When the cardinality is many:
            - The data is of type "collection_model_binding_data" - all messages are sent
              in a single function invocation
            - collection_model_binding_data has 1 or more model_binding_data objects
            - Return a list of ClientReceiveMessage objects
        """
        if data is None or data.type is None:
            return None

        try:
            return ClientReceiveMessage(data=data).get_sdk_type()
        except Exception as e:
            raise ValueError(
                "Failed to decode incoming Office365 Connector batch: "
                + repr(e)
            ) from e
