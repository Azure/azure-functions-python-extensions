"""
Azure Functions MCP STDIO Adapter

A Python extension for Azure Functions that acts as an adapter between MCP servers
running on STDIO and HTTP clients. This adapter surfaces STDIO-based MCP servers
as streamable HTTP endpoints without modifying the underlying MCP server behavior.
"""

# This is a namespace package to allow coexistence with other azurefunctions packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .extensions.mcp_server.decorators.mcp_app import MCPFunctionApp
from .extensions.mcp_server.models.configuration import (
    MCPServerStdioParams,
    MCPStdioConfiguration,
)
from .extensions.mcp_server.models.enums import MCPMode

__version__ = "0.1.0"
__all__ = [
    "MCPFunctionApp",
    "MCPStdioConfiguration",
    "MCPServerStdioParams",
    "MCPMode",
]
