"""
Azure Functions MCP STDIO Adapter Package

This package provides functionality to adapt STDIO-based MCP servers
to streamable HTTP endpoints within Azure Functions.
"""

__version__ = "0.1.0a5"
__author__ = "Microsoft Corporation"
__email__ = "noreply@microsoft.com"

from .decorators.mcp_app import MCPFunctionApp
from .models.configuration import AuthConfiguration, AuthMethod, MCPServerStdioParams, MCPStdioConfiguration
from .models.enums import MCPMode

__all__ = [
    "MCPFunctionApp",
    "MCPStdioConfiguration",
    "MCPServerStdioParams",
    "MCPMode",
    "AuthConfiguration",
    "AuthMethod",
]
