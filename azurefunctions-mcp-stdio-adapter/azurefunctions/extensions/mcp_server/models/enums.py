"""
Enumerations for the MCP STDIO adapter.
"""

from enum import Enum


class MCPMode(Enum):
    """
    Enumeration of supported MCP adapter modes.

    Currently only STDIO mode is supported, which adapts STDIO-based
    MCP servers to streamable HTTP endpoints.
    """

    STDIO = "stdio"

    def __str__(self) -> str:
        return self.value


class MCPServerStatus(Enum):
    """
    Enumeration of MCP server process states.
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class ConfigurationFormat(Enum):
    """
    Enumeration of supported configuration formats.
    """

    MCP_SERVERS = "mcpServers"  # Format 1: {"mcpServers": {...}}
    SERVERS = "servers"  # Format 2: {"servers": {...}}
    MCP_SERVER = "mcp.server"  # Format 3: {"mcp": {"server": {...}}}

    def __str__(self) -> str:
        return self.value
