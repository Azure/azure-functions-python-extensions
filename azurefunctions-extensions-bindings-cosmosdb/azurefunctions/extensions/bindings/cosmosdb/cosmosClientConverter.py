#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Any

from azurefunctions.extensions.base import Datum, InConverter, OutConverter

from .cosmosClient import CosmosClient
from .databaseProxy import DatabaseProxy
from .containerProxy import ContainerProxy


class CosmosClientConverter(
    InConverter,
    OutConverter,
    binding="cosmosDB"
):
    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        return issubclass(
            pytype, (CosmosClient, DatabaseProxy, ContainerProxy)
        )

    @classmethod
    def decode(cls, data: Datum, *, trigger_metadata, pytype) -> Any:
        if data is None or data.type is None:
            return None

        data_type = data.type

        if data_type == "model_binding_data":
            data = data.value
        else:
            raise ValueError(
                f'unexpected type of data received for the "Cosmos" binding '
                f": {data_type!r}"
            )

        # Determines which sdk type to return based on pytype
        if pytype == CosmosClient:
            return CosmosClient(data=data).get_sdk_type()
        elif pytype == DatabaseProxy:
            return DatabaseProxy(data=data).get_sdk_type()
        elif pytype == ContainerProxy:
            return ContainerProxy(data=data).get_sdk_type()
        else:
            return None
