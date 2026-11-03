#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""SDK metadata bindings for OneDrive for Business connector triggers."""

from ..connectorConverter import ConnectorConverter
from .blobMetadata import BlobMetadata

__all__ = ["BlobMetadata", "ConnectorConverter"]
