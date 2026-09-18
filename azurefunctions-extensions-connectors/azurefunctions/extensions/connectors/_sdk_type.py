#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""Base SDK type for connector-specific payload deserialization."""

from __future__ import annotations

from typing import Callable, Generic, TypeVar

from azurefunctions.extensions.base import Datum, SdkType

ResultT = TypeVar("ResultT")


class ConnectorSdkType(SdkType, Generic[ResultT]):
    """Delegate connector payload conversion to a type-specific deserializer."""

    _deserialize: Callable[[Datum], ResultT]

    def __init__(self, *, data: Datum) -> None:
        self._json_payload = data

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """Connector SDK types do not support deferred binding."""
        return False

    def get_sdk_type(self) -> ResultT:
        """Deserialize the stored trigger payload into its Azure SDK type."""
        if self._json_payload is None:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                "No data provided."
            )

        try:
            return self._deserialize(self._json_payload)
        except Exception as error:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"Exception: {error}"
            ) from error
