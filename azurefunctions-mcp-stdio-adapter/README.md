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

The adapter supports multiple JSON configuration formats:

### Format 1: mcpServers
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

### Format 2: servers
```json
{
  "servers": {
    "mysql": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "mysql-mcp-server", "mysql_mcp_server"],
      "env": {
        "MYSQL_HOST": "localhost"
      }
    }
  }
}
```

### Format 3: mcp.server
```json
{
  "mcp": {
    "server": {
      "fabric-rti-mcp": {
        "command": "uvx",
        "args": ["microsoft-fabric-rti-mcp"],
        "env": {
          "KUSTO_SERVICE_URI": "https://help.kusto.windows.net/"
        }
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
