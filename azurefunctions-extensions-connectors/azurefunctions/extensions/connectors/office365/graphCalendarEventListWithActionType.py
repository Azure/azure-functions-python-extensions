#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import List

from azure.connectors.office365 import (
    GraphCalendarEventListWithActionType as AzureGraphCalendarEventListWithActionType
)
from azurefunctions.extensions.base import Datum, SdkType


class GraphCalendarEventListWithActionType(
    SdkType, AzureGraphCalendarEventListWithActionType
):
    def __init__(self, *, data: Datum) -> None:
        self._json_payload = data

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """Office365 connector does not support deferred binding."""
        return False

    def get_sdk_type(
        self
    ) -> List[AzureGraphCalendarEventListWithActionType]:
        """
        Uses the from_json method to parse the JSON payload into a list of
        GraphCalendarEventListWithActionType objects.

        Returns:
            List of GraphCalendarEventListWithActionType objects parsed from
            the JSON payload.
        """
        if not self._json_payload:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"No data provided."
            )

        try:
            # Use the Azure SDK's from_json method to parse the payload
            messages = AzureGraphCalendarEventListWithActionType.from_json(
                self._json_payload
            )
            return messages
        except Exception as e:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"Exception: {e}"
            ) from e
