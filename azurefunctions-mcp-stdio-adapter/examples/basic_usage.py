"""
Basic usage example for Azure Functions MCP STDIO Adapter.

This example shows how to create a simple MCP Function App
with programmatic configuration.
"""

import azure.functions as func
from azurefunctions.extensions.mcp_server import (
    MCPFunctionApp,
    MCPMode,
    MCPStdioConfiguration,
    MCPServerStdioParams,
)

# Configure the MCP server parameters
git_server_params = MCPServerStdioParams(
    command="uvx",
    args=["mcp-server-git"],
    env={"GIT_REPO_PATH": "/path/to/your/git/repository"},
    timeout_seconds=30,
    restart_on_failure=True,
)

# Create the MCP server configuration
git_mcp_config = MCPStdioConfiguration(
    name="git-tools",
    params=git_server_params,
    description="Git repository tools MCP server",
)

# Create the Azure Function App with MCP adapter
app = MCPFunctionApp(
    mode=MCPMode.STDIO, mcp_server=git_mcp_config, auth_level=func.AuthLevel.FUNCTION
)

# The app automatically creates an HTTP endpoint at /api/mcp
# that proxies requests to the STDIO MCP server
