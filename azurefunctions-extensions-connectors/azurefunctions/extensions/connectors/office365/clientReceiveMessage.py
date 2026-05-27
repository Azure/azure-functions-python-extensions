#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import List, Union

from azure.connectors.office365 import ClientReceiveMessage as AzureClientReceiveMessage
from azurefunctions.extensions.base import Datum, SdkType


class ClientReceiveMessage(SdkType, AzureClientReceiveMessage):
    def __init__(self, *, data: Datum) -> None:
        self._json_payload = data

    @classmethod
    def supports_deferred_binding(cls) -> bool:
        """Office365 connector does not support deferred binding."""
        return False

    def get_sdk_type(
        self
    ) -> Union[AzureClientReceiveMessage, List[AzureClientReceiveMessage]]:
        """
        Uses the from_json method to parse the JSON payload into a list of
        ClientReceiveMessage objects.

        Returns:
            Single ClientReceiveMessage object parsed from the JSON payload OR
            List of ClientReceiveMessage objects parsed from the JSON payload.

            Whether it's a single object or a list depends on the structure
            of the JSON payload and is handled by the SDK.
        """
        if not self._json_payload:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"No data provided."
            )

        try:
            # Use the Azure SDK's from_json method to parse the payload
            messages = AzureClientReceiveMessage.from_json(self._json_payload)
            return messages
        except Exception as e:
            raise ValueError(
                f"Unable to create {self.__class__.__name__} SDK type. "
                f"Exception: {e}"
            ) from e
