#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import collections.abc
from typing import Any, Optional, get_args, get_origin

from azurefunctions.extensions.base import Datum, InConverter, OutConverter
from .kafkaRecord import KafkaRecord


class KafkaRecordConverter(
    InConverter,
    OutConverter,
    binding="kafka",
    trigger="kafkaTrigger",
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        if pytype is None:
            return False

        if isinstance(pytype, type) and issubclass(pytype, KafkaRecord):
            return True

        return cls._is_iterable_supported_type(pytype)

    @classmethod
    def _is_iterable_supported_type(cls, annotation: type) -> bool:
        base_type = get_origin(annotation)
        if base_type is None or not issubclass(base_type, collections.abc.Iterable):
            return False

        inner_types = get_args(annotation)
        if inner_types is None or len(inner_types) != 1:
            return False

        inner_type = inner_types[0]
        return isinstance(inner_type, type) and issubclass(inner_type, KafkaRecord)

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Optional[Any]:
        """
        Kafka allows for batches. This means the cardinality can be one or many.
        When the cardinality is one:
            - data is of type "model_binding_data"
        When the cardinality is many:
            - data is of type "collection_model_binding_data"
        """
        if data is None or data.type is None:
            return None

        if data.type == "collection_model_binding_data":
            try:
                return [
                    KafkaRecord(data=mbd).get_sdk_type()
                    for mbd in data.value.model_binding_data
                ]
            except Exception as e:
                raise ValueError(
                    "Failed to decode incoming Kafka batch: " + repr(e)
                ) from e

        if data.type == "model_binding_data":
            return KafkaRecord(data=data.value).get_sdk_type()

        raise ValueError(
            "Unexpected type of data received for the 'kafka' binding: "
            + repr(data.type)
        )
