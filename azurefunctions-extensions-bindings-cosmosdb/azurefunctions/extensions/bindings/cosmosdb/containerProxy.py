#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

import json

from azure.cosmos import ContainerProxy as ContainerProxySdk
from azurefunctions.extensions.base import Datum, SdkType
from .utils import get_connection_string, using_managed_identity, get_cosmos_client


class ContainerProxy(SdkType):
    def __init__(self, *, data: Datum) -> None:
        # model_binding_data properties
        self._data = data
        self._version = None
        self._source = None
        self._content_type = None
        self._database_name = None
        self._container_name = None
        self._connection = None
        self._using_managed_identity = False
        self._preferred_locations = None
        if self._data:
            self._version = data.version
            self._source = data.source
            self._content_type = data.content_type
            content_json = json.loads(data.content)
            self._database_name = content_json.get("DatabaseName")
            self._container_name = content_json.get("ContainerName")
            self._connection = get_connection_string(content_json.get("Connection"))
            self._using_managed_identity = using_managed_identity(
                content_json.get("Connection")
            )
            self._preferred_locations = content_json.get("PreferredLocations")

    def get_sdk_type(self) -> ContainerProxySdk:
        """
        There are two ways to create a CosmosClient:
        1. Through the constructor: this is the only option when using Managed Identity
        2. Through from_connection_string: when not using Managed Identity

        We track if Managed Identity is being used through a flag.
        """
        if not self._data:
            raise ValueError(f"Unable to create {self.__class__.__name__} SDK type.")

        cosmos_client = get_cosmos_client(self._using_managed_identity, 
                                          self._connection, self._preferred_locations)
        db_client = cosmos_client.get_database_client(self._database_name)
        return db_client.get_container_client(self._container_name)
