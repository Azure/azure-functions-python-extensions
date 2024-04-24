#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

from typing import Any

from azurefunctions.extensions.base import Datum, InConverter, OutConverter

from .blobClient import BlobClient
from .containerClient import ContainerClient
from .storageStreamDownloader import StorageStreamDownloader

from .aio.blobClient import BlobClient as AioBlobClient
from .aio.containerClient import ContainerClient as AioContainerClient
from .aio.storageStreamDownloader import StorageStreamDownloader as AioStorageStreamDownloader


class BlobClientConverter(
    InConverter,
    OutConverter,
    binding="blob",
    trigger="blobTrigger",
):

    @classmethod
    def check_input_type_annotation(cls, pytype: type) -> bool:
        return issubclass(
            pytype, (BlobClient, ContainerClient, StorageStreamDownloader,
                     AioBlobClient, AioContainerClient, AioStorageStreamDownloader)
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
                f'unexpected type of data received for the "blob" binding '
                f": {data_type!r}"
            )

        # Determines which sdk type to return based on pytype
        if pytype == BlobClient:
            return BlobClient(data=data).get_sdk_type()
        elif pytype == ContainerClient:
            return ContainerClient(data=data).get_sdk_type()
        elif pytype == StorageStreamDownloader:
            return StorageStreamDownloader(data=data).get_sdk_type()
        elif pytype == AioBlobClient:
            return AioBlobClient(data=data).get_sdk_type()
        elif pytype == AioContainerClient:
            return AioContainerClient(data=data).get_sdk_type()
        elif pytype == AioStorageStreamDownloader:
            return AioStorageStreamDownloader(data=data).get_sdk_type()
        else:
            return None
