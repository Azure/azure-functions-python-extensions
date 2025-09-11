#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Any

from azurefunctions.extensions.base import InConverter
from .serviceBusMessageActions import ServiceBusMessageActions


class ServiceBusClientConverter(
    InConverter,
    binding='serviceBusClient'
):

    @classmethod
    def get_client(cls) -> Any:
        """
        Returns an instance of ServiceBusMessageActions.
        """
        return ServiceBusMessageActions.get_instance()
