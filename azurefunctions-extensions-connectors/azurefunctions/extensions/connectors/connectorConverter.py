#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import collections.abc
from typing import Any, Optional, get_args, get_origin

from azurefunctions.extensions.base import Datum, InConverter
from ._sdk_type import ConnectorSdkType


class ConnectorConverter(
    InConverter,
    binding='connectorTrigger', trigger=True
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        if pytype is None:
            return False

        # The annotation is a class/type (not an object) - not iterable
        if (isinstance(pytype, type)
                and issubclass(pytype, ConnectorSdkType)):
            return True

        # An iterable who only has one inner type and is a subclass of
        # a supported SDK type
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
                and issubclass(inner_type, ConnectorSdkType))

    @classmethod
    def _get_sdk_type(cls, pytype: type) -> Optional[type]:
        """
        Extract the SDK type from the annotation, handling both direct types
        and List[Type] annotations.
        """
        # Direct type check
        if isinstance(pytype, type) and issubclass(pytype, ConnectorSdkType):
            return pytype

        # Check for List[Type] and extract inner type
        if cls._is_iterable_supported_type(pytype):
            inner_types = get_args(pytype)
            if inner_types and len(inner_types) == 1:
                return inner_types[0]

        return None

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Optional[Any]:
        """
        Connector triggers can have one or many values. The selected SDK type
        handles the connector-specific payload shape.
        """
        if data is None or data.type is None:
            return None

        # Extract the SDK type, handling both Type and List[Type]
        sdk_type = cls._get_sdk_type(pytype)

        try:
            if sdk_type is None:
                return None

            return sdk_type(data=data).get_sdk_type()
        except Exception as e:
            raise ValueError(
                "Failed to decode incoming connector payload: "
                + repr(e)
            ) from e
