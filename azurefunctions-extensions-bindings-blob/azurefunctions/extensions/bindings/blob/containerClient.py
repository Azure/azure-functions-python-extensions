#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from azurefunctions.extensions.base import Datum
from .blobSdkType import BlobSdkType


class ContainerClient(BlobSdkType):
    def __init__(self, *, data: Datum) -> None:
        super().__init__(data=data)

    # Returns a ContainerClient
    def get_sdk_type(self):
        blob_service_client = super().get_sdk_type()
        try:
            return blob_service_client.get_container_client(
                container=self._containerName
            )
        except Exception as e:
            raise ValueError(f"Unable to create {self.__class__.__name__} SDK type."
                             f"Exception: {e}")
