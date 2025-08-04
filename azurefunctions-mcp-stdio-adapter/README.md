# Azure Functions MCP STDIO Adapter

A Python extension for Azure Functions that acts as an adapter between MCP (Model Context Protocol) servers running on STDIO and HTTP clients. This adapter surfaces STDIO-based MCP servers as streamable HTTP endpoints without modifying the underlying MCP server behavior.

## Overview

The Azure Functions MCP STDIO Adapter enables seamless integration between:

- **Input**: Python MCP servers that communicate via STDIO (JSON-RPC over stdin/stdout with Content-Length framing)
- **Output**: Azure Functions HTTP endpoints that expose streamable HTTP responses
- **Transport**: Maintains protocol parity without modifying customer MCP servers

### Data Flow Diagram

```
Client ⇄ HTTP Stream ⇄ Azure Function Adapter ⇄ STDIO ⇄ MCP Server
      │                     │                  │           │
      │                     │                  │           └─ Customer's MCP Server
      │                     │                  └─ JSON-RPC over STDIO
      │                     └─ Process Management & Forwarding
      └─ Streamable HTTP Responses
```

## Features

- **Multi-format Configuration Support**: Supports various JSON configuration formats
- **Process Lifecycle Management**: Automatic start, monitor, and graceful shutdown of MCP servers
- **Streaming HTTP Integration**: Uses MCP SDK's StreamableHTTPSessionManager for real-time communication  
- **UVX Integration**: Supports `uvx` (uv tool run) for running MCP servers without global installation
- **Error Recovery**: Handles MCP server crashes and reconnection scenarios
- **Environment Variable Support**: Passes through environment variables to MCP servers
- **Well-known Configuration Files**: Supports loading from standard file locations

## Session Isolation & Multi-Tenancy

The Azure Functions MCP STDIO Adapter provides **best-effort session isolation** for multi-tenant scenarios while maintaining optimal resource utilization.

### Session-to-Process Mapping

Each unique session gets its own dedicated MCP server process, ensuring proper isolation between different clients:

```text
Session ID → Adapter Instance → Process Manager → MCP Server Process
session-1  →   adapter_1     →   process_1    →     PID 1001
session-2  →   adapter_2     →   process_2    →     PID 1002
session-3  →   adapter_3     →   process_3    →     PID 1003
```

### How It Works

#### Session Lifecycle

```python
# Client A connects with session-1
GET /mcp HTTP/1.1
mcp-session-id: session-1
# → Creates new MCPStdioAdapter instance → Spawns new MCP server process

# Client A makes multiple calls - all use the same process
POST /mcp HTTP/1.1
mcp-session-id: session-1
{"method": "initialize", ...}     # → process_1

POST /mcp HTTP/1.1  
mcp-session-id: session-1
{"method": "tools/list", ...}     # → process_1

POST /mcp HTTP/1.1
mcp-session-id: session-1  
{"method": "tools/call", ...}     # → process_1

# Client B connects with session-2 (concurrent)
GET /mcp HTTP/1.1
mcp-session-id: session-2
# → Creates SEPARATE MCPStdioAdapter → Spawns SEPARATE MCP server process

POST /mcp HTTP/1.1
mcp-session-id: session-2
{"method": "initialize", ...}     # → process_2 (ISOLATED!)
```

#### Session Isolation Guarantees

1. **Process Isolation**: Each session runs in its own MCP server subprocess

   ```python
   # Each session maintains separate process state
   session_adapters = {
       "session-1": MCPStdioAdapter(process_1),  # PID 1001
       "session-2": MCPStdioAdapter(process_2),  # PID 1002  
       "session-3": MCPStdioAdapter(process_3),  # PID 1003
   }
   ```

2. **Memory Isolation**: Each adapter has independent buffers and state

   ```python
   # Session 1's adapter state
   adapter_1._read_buffer = b"session_1_data"
   adapter_1._session_state = "initialized"
   
   # Session 2's adapter state (completely separate)  
   adapter_2._read_buffer = b"session_2_data"
   adapter_2._session_state = "uninitialized"
   ```

3. **Communication Isolation**: Each session has dedicated STDIO channels

   ```python
   # No cross-session message contamination
   adapter_1.process_manager.stdin  # → process_1 stdin
   adapter_2.process_manager.stdin  # → process_2 stdin
   
   adapter_1.process_manager.stdout # ← process_1 stdout  
   adapter_2.process_manager.stdout # ← process_2 stdout
   ```

### Session Management

#### Session Headers

Sessions are identified via HTTP headers:

```http
POST /mcp HTTP/1.1
mcp-session-id: client-unique-session-id
Content-Type: application/json

{"jsonrpc": "2.0", "method": "tools/list", "id": 1}
```

#### Automatic Session Creation

If no session ID is provided, the adapter generates one:

```python
# Client request without session ID
session_id = req.headers.get("mcp-session-id")
if not session_id:
    session_id = str(uuid.uuid4()).replace("-", "")  # Generate new session
    # New adapter and process created automatically
```

#### Session Persistence

Sessions persist across multiple HTTP requests:

```python
# Session state maintained in memory
class MCPSessionState:
    session_id: str
    is_initialized: bool = False
    initialization_response: Optional[Dict[str, Any]] = None
    last_activity: float = 0.0  # Auto-cleanup after timeout
```

### Best-Effort Multi-Tenancy

#### What "Best-Effort" Means

✅ **Guaranteed Isolation:**
- Each session has its own MCP server process
- Memory spaces are completely separate  
- STDIO communication channels are isolated
- Session state is tracked independently

⚠️ **Azure Functions Shared Environment:**
- Sessions share the same Azure Functions runtime
- Sessions share the same file system
- Sessions share network and system resources
- No cryptographic isolation between sessions

#### Resource Management

```python
# Automatic resource cleanup
class MCPSessionManager:
    def __init__(self, session_timeout_seconds: float = 3600):  # 1 hour default
        self._sessions: Dict[str, MCPSessionState] = {}
        
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions and their processes"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, session in self._sessions.items()
            if current_time - session.last_activity > self._session_timeout
        ]
        
        for session_id in expired_sessions:
            # Clean up adapter and terminate process
            await self._cleanup_session(session_id)
```

#### Recommended Usage Patterns

1. **Trusted Multi-Tenancy**: Use for scenarios where tenants are trusted (e.g., different teams in same organization)

2. **Development/Testing**: Ideal for development environments with multiple concurrent users

3. **Microservice Integration**: Perfect for multiple services calling the same MCP functionality

4. **Session-Aware Applications**: Applications that maintain client state across multiple MCP calls

### Limitations & Considerations

#### Security Considerations
- **File System Access**: MCP servers can access the same file system
- **Environment Variables**: Shared environment between sessions  
- **Network Access**: Sessions share network interfaces
- **Process Visibility**: Processes may be visible to each other

#### Resource Limits
- **Memory Usage**: Multiple processes increase memory consumption
- **Process Limits**: Azure Functions has process count limitations
- **Connection Limits**: Each session maintains persistent connections

#### Best Practices
```python
# 1. Use unique session IDs per client
session_id = f"client-{client_id}-{timestamp}"

# 2. Implement proper session cleanup
@app.function_name("cleanup_sessions")
@app.timer_trigger(schedule="0 */30 * * * *")  # Every 30 minutes
async def cleanup_expired_sessions(timer: func.TimerRequest):
    await session_manager.cleanup_expired_sessions()

# 3. Monitor resource usage
@app.function_name("session_metrics")  
@app.http_trigger(methods=["GET"])
async def get_session_metrics(req: func.HttpRequest):
    return {
        "active_sessions": len(session_adapters),
        "total_processes": sum(1 for adapter in session_adapters.values() 
                              if adapter.is_connected)
    }
```

### Configuration for Multi-Tenancy

```json
{
  "mcpServers": {
    "shared-mcp-server": {
      "command": "uvx",
      "args": ["your-mcp-server"],
      "env": {
        "MAX_CONCURRENT_SESSIONS": "10",
        "SESSION_TIMEOUT_SECONDS": "3600"
      },
      "timeout_seconds": 30,
      "restart_on_failure": true,
      "max_restarts": 3
    }
  }
}
```

This architecture provides robust session isolation suitable for most multi-tenant Azure Functions scenarios while maintaining the flexibility and performance benefits of the MCP protocol.

## Authentication & Authorization

The Azure Functions MCP STDIO Adapter provides comprehensive authentication support for both Azure and non-Azure MCP servers, enabling secure remote access with proper token handling and On-Behalf-Of (OBO) flows.

### Authentication Architecture

```text
Client Request → Azure Functions → Auth Provider → MCP Server Process
     ↓               ↓               ↓               ↓
Bearer Token → Token Validation → Env Variables → Authenticated SDK
```

### Supported Authentication Methods

#### 1. No Authentication (`none`)
For development, testing, or internal-only MCP servers:

```json
{
  "mcpServers": {
    "internal-tools": {
      "command": "uvx",
      "args": ["internal-mcp-server"],
      "auth": {
        "method": "none"
      }
    }
  }
}
```

#### 2. Azure Default Credentials (`azure_default`)
Uses Azure Managed Identity when deployed, DefaultAzureCredential locally:

```json
{
  "mcpServers": {
    "azure-resources": {
      "command": "uvx", 
      "args": ["azure-resource-mcp"],
      "auth": {
        "method": "azure_default",
        "azure_scopes": [
          "https://management.azure.com/.default"
        ],
        "forward_user_token": false
      }
    }
  }
}
```

**Use Cases:**
- MCP servers that need to access Azure resources with the function's identity
- Scenarios where the MCP server itself needs Azure permissions
- Backend services that don't need user context

#### 3. Azure On-Behalf-Of (`azure_obo`)
**Perfect for Fabric RTI and similar scenarios** - forwards user tokens to Azure services:

```json
{
  "mcpServers": {
    "fabric-rti-mcp": {
      "command": "uvx",
      "args": ["microsoft-fabric-rti-mcp"],
      "env": {
        "KUSTO_SERVICE_URI": "https://help.kusto.windows.net/",
        "KUSTO_SERVICE_DEFAULT_DB": "Samples"
      },
      "auth": {
        "method": "azure_obo",
        "azure_client_id": "${AZURE_CLIENT_ID}",
        "azure_client_secret": "${AZURE_CLIENT_SECRET}",
        "azure_scopes": [
          "https://management.azure.com/.default",
          "https://fabric.microsoft.com/.default"
        ],
        "forward_user_token": true
      }
    }
  }
}
```

**Environment Variables Set for MCP Server:**
```bash
AZURE_CLIENT_ID=your-app-registration-id
AZURE_CLIENT_SECRET=your-client-secret  
AZURE_TENANT_ID=extracted-from-user-token
AZURE_USER_ASSERTION=original-user-token
AZURE_USE_OBO=true
```

**Use Cases:**
- Fabric RTI MCP servers accessing user's Fabric workspaces
- Any Azure service requiring user context (SharePoint, Graph, etc.)
- Multi-tenant applications with user-specific data access

#### 4. Generic OAuth2 Bearer (`oauth2_bearer`)
For non-Azure OAuth2 providers (Google, GitHub, custom identity providers):

```json
{
  "mcpServers": {
    "github-tools": {
      "command": "uvx",
      "args": ["github-mcp-server"],
      "auth": {
        "method": "oauth2_bearer",
        "oauth2_required_scopes": [
          "repo:read",
          "user:read"
        ],
        "oauth2_issuer": "https://github.com",
        "forward_user_token": true
      }
    }
  }
}
```

**Environment Variables Set for MCP Server:**
```bash
OAUTH_ACCESS_TOKEN=user-provided-token
OAUTH_USER_ID=extracted-user-id
OAUTH_SCOPES=repo:read user:read
```

### Client-Side Authentication

#### HTTP Headers Required

All authenticated requests must include the `Authorization` header:

```http
POST /api/mcp HTTP/1.1
Host: your-function-app.azurewebsites.net
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
mcp-session-id: session-12345

{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}
```

#### MCP Client Configuration

When using the MCP SDK, configure HTTP transport with authentication:

```python
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters
from mcp.client.sse import SseServerParameters

# For HTTP streaming with auth
server = SseServerParameters(
    url="https://your-function-app.azurewebsites.net/api/mcp",
    headers={
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
)

async with ClientSession(server) as session:
    # Use authenticated session
    result = await session.call_tool("list_files", {"path": "/"})
```

### Azure Active Directory Integration

#### App Registration Setup

1. **Create App Registration** in Azure Portal
2. **Configure API Permissions** for target services:
   ```text
   - Microsoft Graph: User.Read
   - Azure Service Management: user_impersonation  
   - Power BI Service: Dataset.Read.All (for Fabric)
   ```
3. **Generate Client Secret**
4. **Configure Application Settings**:
   ```bash
   AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789012
   AZURE_CLIENT_SECRET=your-secret-value
   ```

#### Token Acquisition Flow

```typescript
// Client-side token acquisition (JavaScript example)
import { PublicClientApplication } from "@azure/msal-browser";

const msalConfig = {
    auth: {
        clientId: "your-client-id",
        authority: "https://login.microsoftonline.com/your-tenant"
    }
};

const pca = new PublicClientApplication(msalConfig);

// Get token for MCP server access
const tokenRequest = {
    scopes: [
        "https://management.azure.com/.default",
        "https://fabric.microsoft.com/.default"
    ]
};

const response = await pca.acquireTokenSilent(tokenRequest);
const accessToken = response.accessToken;

// Use token with MCP client
const mcpClient = new McpClient({
    url: "https://your-function.azurewebsites.net/api/mcp",
    headers: {
        "Authorization": `Bearer ${accessToken}`
    }
});
```

### Error Handling

#### Authentication Errors

The adapter returns standard HTTP status codes for auth failures:

```json
// 401 Unauthorized - Missing or invalid token
{
  "error": {
    "code": "authentication_required",
    "message": "Missing or invalid Authorization header"
  }
}

// 403 Forbidden - Insufficient scopes  
{
  "error": {
    "code": "insufficient_scopes", 
    "message": "Token missing required scopes: repo:write"
  }
}
```

#### Debugging Authentication

Enable debug logging to troubleshoot auth issues:

```python
import logging
logging.getLogger("azurefunctions.extensions.mcp_server.auth").setLevel(logging.DEBUG)
```

### Security Considerations

#### Token Validation
- Bearer tokens are parsed for claims extraction
- **Production deployments should implement proper JWT signature verification**
- Tokens are validated for required scopes before processing

#### Token Storage
- User tokens are only stored in memory during request processing
- Tokens are passed to MCP servers via environment variables
- No persistent token storage in the adapter

#### Environment Isolation
- Each session gets isolated environment variables
- Authentication credentials are scoped to individual MCP server processes
- No credential sharing between sessions

### Best Practices

#### For Azure MCP Servers
```json
{
  "auth": {
    "method": "azure_obo",
    "azure_scopes": [
      "https://management.azure.com/.default"  // Be specific about scopes
    ],
    "forward_user_token": true  // Enable for user context
  }
}
```

#### For Non-Azure MCP Servers
```json
{
  "auth": {
    "method": "oauth2_bearer", 
    "oauth2_required_scopes": ["read:data"],  // Validate required scopes
    "forward_user_token": true
  }
}
```

#### Environment Variables
```bash
# Use Azure App Settings for secrets
AZURE_CLIENT_SECRET="@Microsoft.KeyVault(SecretUri=https://vault.vault.azure.net/secrets/client-secret/)"

# Reference environment variables in config
"azure_client_id": "${AZURE_CLIENT_ID}"
```

This authentication architecture ensures secure, scalable access to MCP servers while supporting both Azure-native and generic OAuth2 authentication patterns.

## Installation

```bash
# Install with UV (recommended)
uv add azurefunctions-mcp-stdio-adapter

# Or with pip
pip install azurefunctions-mcp-stdio-adapter
```

## Quick Start

### Configuration-Only Usage

1. Create a configuration file `mcp_config.json`:

```json
{
  "mcpServers": {
    "git-tools": {
      "command": "uvx",
      "args": ["mcp-server-git"],
      "env": {
        "GIT_REPO_PATH": "/path/to/your/repo"
      }
    }
  }
}
```

2. Create your Azure Function app:

```python
from azurefunctions.extensions.mcp_server import MCPFunctionApp, MCPMode

# Load configuration from file
app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    config_file="mcp_config.json"
)
```

### Programmatic Usage

```python
import azure.functions as func
from azurefunctions.extensions.mcp_server import (
    MCPFunctionApp,
    MCPMode,
    MCPStdioConfiguration,
    MCPServerStdioParams
)

# Define MCP server configuration
git_mcp = MCPStdioConfiguration(
    name="git-tools",
    params=MCPServerStdioParams(
        command="uvx",
        args=["mcp-server-git"],
        env={"GIT_REPO_PATH": "/path/to/repo"}
    )
)

# Create MCP Function App
app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    mcp_server=git_mcp
)
```

## Configuration Formats

The adapter supports JSON configuration files with the following format:

### Standard Configuration Format
```json
{
  "mcpServers": {
    "mssql": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "MSSQL_SERVER": "your_server",
        "MSSQL_DATABASE": "your_database"
      }
    }
  }
}
```

### Example: MySQL Configuration
```json
{
  "mcpServers": {
    "mysql": {
      "command": "uvx",
      "args": ["--from", "mysql-mcp-server", "mysql_mcp_server"],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "your_username",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database"
      }
    }
  }
}
```

### Example: Fabric RTI Configuration  
```json
{
  "mcpServers": {
    "fabric-rti-mcp": {
      "command": "uvx",
      "args": ["microsoft-fabric-rti-mcp"],
      "env": {
        "KUSTO_SERVICE_URI": "https://help.kusto.windows.net/",
        "KUSTO_SERVICE_DEFAULT_DB": "Samples"
      }
    }
  }
}
```

## API Reference

### MCPFunctionApp

The main class for creating Azure Function apps with MCP STDIO adapter functionality.

```python
class MCPFunctionApp:
    def __init__(
        self,
        mode: MCPMode = MCPMode.STDIO,
        mcp_server: Optional[MCPStdioConfiguration] = None,
        config_file: Optional[str] = None,
        auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
        **kwargs
    ):
        """
        Initialize MCP Function App
        
        Args:
            mode: Operating mode (currently only STDIO supported)
            mcp_server: Programmatic MCP server configuration
            config_file: Path to JSON configuration file
            auth_level: Azure Functions authorization level
        """
```

### MCPStdioConfiguration

Configuration container for MCP STDIO servers.

```python
class MCPStdioConfiguration:
    def __init__(
        self,
        name: str,
        params: MCPServerStdioParams
    ):
        """
        MCP STDIO server configuration
        
        Args:
            name: Unique name for the MCP server
            params: Server execution parameters
        """
```

### MCPServerStdioParams

Parameters for STDIO server execution.

```python
class MCPServerStdioParams:
    def __init__(
        self,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None,
        working_dir: Optional[str] = None
    ):
        """
        STDIO server execution parameters
        
        Args:
            command: Command to execute (e.g., "uvx", "python")
            args: Command arguments
            env: Environment variables
            working_dir: Working directory for the process
        """
```

## Deployment

### Local Development

```bash
# Clone and setup
git clone <your-repo>
cd azurefunctions-mcp-stdio-adapter

# Install dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .
```

### Azure Deployment

1. Ensure your `function_app.py` uses the MCP adapter:

```python
from azurefunctions.extensions.mcp_server import MCPFunctionApp, MCPMode

app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    config_file="mcp_config.json"
)
```

2. Deploy using Azure Functions Core Tools:

```bash
func azure functionapp publish <your-function-app-name>
```

## Error Handling

The adapter includes comprehensive error handling:

- **UVX Detection**: Automatically detects missing `uvx` and provides helpful error messages
- **Process Recovery**: Handles MCP server crashes with automatic restart
- **Connection Management**: Manages STDIO connections with proper cleanup
- **Timeout Handling**: Configurable timeouts for process startup and communication

## Logging and Monitoring

Enable detailed logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.INFO)

app = MCPFunctionApp(
    mode=MCPMode.STDIO,
    config_file="mcp_config.json"
)
```

## Troubleshooting

### Common Issues

1. **UVX not found**: Ensure `uvx` is installed and available in PATH
2. **Process startup timeout**: Increase timeout in configuration or check MCP server startup time
3. **STDIO communication errors**: Verify MCP server implements proper Content-Length framing

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## References

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) - Official MCP transport specification
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - STDIO and Streamable HTTP support
- [Azure Functions Python Streaming](https://docs.microsoft.com/azure/azure-functions/functions-reference-python#http-streaming) - Azure Functions HTTP streaming documentation
- [UVX Documentation](https://docs.astral.sh/uv/guides/tools/) - UV tool runner documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `uv run pytest`
6. Format code: `uv run black . && uv run isort .`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:

- [GitHub Issues](https://github.com/Azure/azure-functions-python-extensions/issues)
- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [MCP Community](https://github.com/modelcontextprotocol)
