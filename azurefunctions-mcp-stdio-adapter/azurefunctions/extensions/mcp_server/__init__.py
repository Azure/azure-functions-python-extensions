"""
Azure Functions MCP STDIO Adapter Package

This package provides functionality to adapt STDIO-based MCP servers
to streamable HTTP endpoints within Azure Functions.
"""

from .decorators.mcp_app import MCPFunctionApp
from .models.configuration import MCPServerStdioParams, MCPStdioConfiguration
from .models.enums import MCPMode

__all__ = [
    "MCPFunctionApp",
    "MCPStdioConfiguration",
    "MCPServerStdioParams",
    "MCPMode",
]
