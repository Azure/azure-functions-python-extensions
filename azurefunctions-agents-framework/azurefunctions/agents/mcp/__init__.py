# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""MCP (Model Context Protocol) support for Azure Functions Agent Framework.

This module provides support for integrating MCP servers and tools into Azure Function agents,
enabling rich tool integration capabilities following the Model Context Protocol specification.
"""

from .server import (
    MCPServer,
    MCPServerStdioParams,
    MCPServerSseParams,
    MCPServerStreamableHttpParams,
)
from .util import MCPUtil
from ..types import MCPServerMode

__all__ = [
    "MCPServer",
    "MCPServerMode",
    "MCPServerStdioParams",
    "MCPServerSseParams", 
    "MCPServerStreamableHttpParams",
    "MCPUtil",
]
