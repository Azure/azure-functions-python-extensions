"""
Git MCP Server Function App Test.

This example demonstrates how to create an Azure Function App
that uses the git MCP server for repository operations.
"""

import azure.functions as func
from azurefunctions.extensions.mcp_server import (
    MCPFunctionApp,
    MCPMode,
    MCPStdioConfiguration,
    MCPServerStdioParams
)

# Configure the Git MCP server parameters
# You can change the repository path to any git repository you want to test with
git_server_params = MCPServerStdioParams(
    command="uvx",
    args=["mcp-server-git", "--repository", "/Users/varadmeru/work/microsoft/azfunctions/azfuncpyworker"],
    env={},  # No need for GIT_REPO_PATH env var with the new format
    timeout_seconds=30,
    restart_on_failure=True
)

# Configure the Random Number MCP server parameters for testing
random_mcp_params = MCPServerStdioParams(
    command="uvx",
    args=["random-number-mcp"],
    env={}
)

# Create the MCP server configuration
git_mcp_config = MCPStdioConfiguration(
    name="git-tools",
    params=git_server_params,
    description="Git repository tools MCP server for testing"
)

# Create the Random Number MCP server configuration
random_mcp_config = MCPStdioConfiguration(
    name="random-number-generator",
    params=random_mcp_params,
    description="Random number generator MCP server for testing"
)

# Create the Azure Function App with MCP adapter
# Using config file instead of programmatic configuration
app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    # mcp_server=random_mcp_config,  # Uncomment to use programmatic config
    config_file="mcp_config.json",
    auth_level=func.AuthLevel.FUNCTION,
    name="MCP Test Server"
)
