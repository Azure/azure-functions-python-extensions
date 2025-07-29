"""
Complete Function App sample using configuration file.

This example demonstrates how to create an Azure Function App
that loads MCP server configuration from a JSON file.
"""

import os
from pathlib import Path

import azure.functions as func
from azurefunctions.extensions.mcp_server import MCPFunctionApp, MCPMode

# Get the directory containing this script
current_dir = Path(__file__).parent

# Path to configuration file
config_file = current_dir / "configurations" / "mysql_config.json"

# Ensure the config file exists
if not config_file.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_file}")

# Create the MCP Function App with file-based configuration
app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    config_file=str(config_file),
    auth_level=func.AuthLevel.FUNCTION,
    name="MySQL MCP Adapter",
    instructions="Azure Functions adapter for MySQL MCP server"
)

# Optional: Add custom endpoint for health check
@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        # Get server statistics
        stats = app.get_server_stats()
        
        return func.HttpResponse(
            body=f"MCP Adapter Health: {stats}",
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return func.HttpResponse(
            body=f"Health check failed: {str(e)}",
            status_code=500
        )

# Optional: Add custom endpoint for server statistics
@app.function_name(name="stats")
@app.route(route="stats", methods=["GET"])
def get_stats(req: func.HttpRequest) -> func.HttpResponse:
    """Get MCP server statistics."""
    try:
        stats = app.get_server_stats()
        
        import json
        return func.HttpResponse(
            body=json.dumps(stats, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return func.HttpResponse(
            body=f"Error getting stats: {str(e)}",
            status_code=500
        )

# The main MCP endpoint is automatically created at /api/mcp
# Additional endpoints:
# - /api/health - Health check
# - /api/stats - Server statistics
