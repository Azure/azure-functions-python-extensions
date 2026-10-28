#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.

"""SDK refresh bindings for Power Query Dataflows connector triggers."""

from ..connectorConverter import ConnectorConverter

try:
    from .refreshModel import RefreshModel
except ModuleNotFoundError as error:
    if error.name != "azure.connectors.dataflows":
        raise
    raise ImportError(
        "Dataflows bindings require an azure-connectors build containing "
        "azure.connectors.dataflows. Install SDK main revision "
        "116d96fa55473217f8e50a11ee523c9b38854bf9 or a later build with that "
        "module; the published 0.5.0b1 package does not contain it."
    ) from error

__all__ = ["ConnectorConverter", "RefreshModel"]
