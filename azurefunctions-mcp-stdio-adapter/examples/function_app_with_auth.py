"""
Example Azure Function with MCP authentication support.

This example demonstrates how to use the MCP STDIO adapter with different
authentication methods for various MCP server scenarios.
"""

import azure.functions as func
from azurefunctions.extensions.mcp_server import MCPFunctionApp
from azurefunctions.extensions.mcp_server.models.configuration import (
    MCPStdioConfiguration,
    MCPServerStdioParams,
    AuthConfiguration,
    AuthMethod,
)

# Example 1: Fabric RTI with On-Behalf-Of Authentication
fabric_config = MCPStdioConfiguration(
    name="fabric-rti-mcp",
    params=MCPServerStdioParams(
        command="uvx",
        args=["microsoft-fabric-rti-mcp"],
        env={
            "KUSTO_SERVICE_URI": "https://help.kusto.windows.net/",
            "KUSTO_SERVICE_DEFAULT_DB": "Samples",
        },
    ),
    auth=AuthConfiguration(
        method=AuthMethod.AZURE_OBO,
        azure_client_id="${AZURE_CLIENT_ID}",  # Set in App Settings
        azure_client_secret="${AZURE_CLIENT_SECRET}",  # Set in App Settings
        azure_scopes=[
            "https://management.azure.com/.default",
            "https://fabric.microsoft.com/.default",
        ],
        forward_user_token=True,
    ),
)

# Create MCP Function App with authentication
app = MCPFunctionApp(
    mcp_server=fabric_config,
    auth_level=func.AuthLevel.FUNCTION,
)


# Example 2: OAuth2 MCP Server (GitHub, etc.)
@app.function_name("github_mcp")
def github_mcp_endpoint():
    """Example of OAuth2 authentication for GitHub MCP server."""
    github_config = MCPStdioConfiguration(
        name="github-mcp",
        params=MCPServerStdioParams(
            command="uvx",
            args=["github-mcp-server"],
            env={"GITHUB_API_BASE": "https://api.github.com"},
        ),
        auth=AuthConfiguration(
            method=AuthMethod.OAUTH2_BEARER,
            oauth2_required_scopes=["repo:read", "user:read"],
            forward_user_token=True,
        ),
    )
    
    return MCPFunctionApp(
        mcp_server=github_config,
        auth_level=func.AuthLevel.FUNCTION,
    )


# Example 3: Azure Default (No user context needed)
@app.function_name("azure_resources_mcp")
def azure_resources_endpoint():
    """Example of Azure Default authentication for resource management."""
    azure_config = MCPStdioConfiguration(
        name="azure-resources",
        params=MCPServerStdioParams(
            command="uvx",
            args=["azure-resource-mcp"],
            env={
                "AZURE_SUBSCRIPTION_ID": "${AZURE_SUBSCRIPTION_ID}",
                "AZURE_RESOURCE_GROUP": "${AZURE_RESOURCE_GROUP}",
            },
        ),
        auth=AuthConfiguration(
            method=AuthMethod.AZURE_DEFAULT,
            azure_scopes=["https://management.azure.com/.default"],
            forward_user_token=False,  # Use function's managed identity
        ),
    )
    
    return MCPFunctionApp(
        mcp_server=azure_config,
        auth_level=func.AuthLevel.FUNCTION,
    )


# Example client usage documentation
"""
Client Usage Examples:

1. JavaScript/TypeScript with MSAL:
```typescript
import { PublicClientApplication } from "@azure/msal-browser";

const msalConfig = {
    auth: {
        clientId: "your-client-id",
        authority: "https://login.microsoftonline.com/your-tenant"
    }
};

const pca = new PublicClientApplication(msalConfig);

// Get token for Fabric access
const tokenRequest = {
    scopes: ["https://fabric.microsoft.com/.default"]
};

const response = await pca.acquireTokenSilent(tokenRequest);

// Use with MCP client
const mcpResponse = await fetch("https://your-function.azurewebsites.net/api/mcp", {
    method: "POST",
    headers: {
        "Authorization": `Bearer ${response.accessToken}`,
        "Content-Type": "application/json",
        "mcp-session-id": "unique-session-id"
    },
    body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/list",
        id: 1
    })
});
```

2. Python with MCP SDK:
```python
from mcp.client.sse import SseServerParameters
from mcp import ClientSession

# Configure authenticated server
server = SseServerParameters(
    url="https://your-function.azurewebsites.net/api/mcp",
    headers={
        "Authorization": f"Bearer {user_token}",
    }
)

async with ClientSession(server) as session:
    # Initialize MCP connection
    await session.initialize()
    
    # List available tools
    tools = await session.list_tools()
    
    # Call a tool
    result = await session.call_tool("query_fabric", {
        "query": "SHOW TABLES"
    })
```

3. cURL for testing:
```bash
# Get access token (using Azure CLI)
TOKEN=$(az account get-access-token --scope https://fabric.microsoft.com/.default --query accessToken -o tsv)

# Call MCP endpoint
curl -X POST "https://your-function.azurewebsites.net/api/mcp" \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -H "mcp-session-id: test-session-123" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```
"""
