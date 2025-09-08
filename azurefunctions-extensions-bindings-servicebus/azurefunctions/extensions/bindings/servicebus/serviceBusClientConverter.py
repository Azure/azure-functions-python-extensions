#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Any

from azurefunctions.extensions.base import Datum, InConverter
from .serviceBusMessageActions import ServiceBusMessageActions


class ServiceBusClientConverter(
    InConverter,
    binding='serviceBusClient'
):

    @classmethod
    def get_client(cls) -> Any:
        """
        TODO: comments
        """
        return ServiceBusMessageActions.get_instance()
