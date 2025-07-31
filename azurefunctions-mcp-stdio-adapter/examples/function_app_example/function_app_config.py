"""
Alternative Git MCP Server Function App using configuration file.

This version uses a JSON configuration file instead of programmatic configuration.
"""

import os
from pathlib import Path

import azure.functions as func
from azurefunctions.extensions.mcp_server import MCPFunctionApp, MCPMode

# Get the directory containing this script
current_dir = Path(__file__).parent

# Path to configuration file (go up one level to configurations directory)
config_file = current_dir.parent / "configurations" / "git_config.json"

# Create the MCP Function App with file-based configuration
app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    config_file=str(config_file),
    auth_level=func.AuthLevel.FUNCTION,
    name="Git MCP Adapter (Config File)",
    instructions="Azure Functions adapter for Git MCP server using config file"
)

# Optional: Add custom endpoints
@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        stats = app.get_server_stats()
        return func.HttpResponse(
            body=f"Git MCP Server Health (Config): {stats}",
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return func.HttpResponse(
            body=f"Health check failed: {str(e)}",
            status_code=500,
            headers={"Content-Type": "text/plain"}
        )
