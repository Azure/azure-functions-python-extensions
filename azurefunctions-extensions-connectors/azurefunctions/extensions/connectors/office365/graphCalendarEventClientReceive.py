#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import List

from azure.connectors.office365 import (
    GraphCalendarEventClientReceive as AzureGraphCalendarEventClientReceive
)
from azurefunctions.extensions.base import Datum, SdkType


class GraphCalendarEventClientReceive(
    SdkType, AzureGraphCalendarEventClientReceive
):
    def __init__(self, *, data: Datum) -> None:
        self._json_payload = data

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """office365 connector does not support deferred binding."""
        return False

    def get_sdk_type(
        self
    ) -> List[AzureGraphCalendarEventClientReceive]:
        """
        Uses the from_json method to parse the JSON payload into a list of
        GraphCalendarEventClientReceive objects.

        This type is the rich payload returned for the following actions:
        - When a new event is created
        - When an event is modified
        - When an upcoming event is starting soon

        Returns:
            List of GraphCalendarEventClientReceive objects parsed from
            the JSON payload.
        """
        if not self._json_payload:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"No data provided."
            )
        try:
            messages = AzureGraphCalendarEventClientReceive.from_json(
                self._json_payload
            )
            return messages
        except Exception as e:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"Exception: {e}"
            ) from e
