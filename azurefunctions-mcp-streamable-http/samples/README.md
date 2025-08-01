# MCP Server with StreamableHTTP Transport Sample

This sample demonstrates how to create a comprehensive MCP (Model Context Protocol) server using Azure Functions and the new StreamableHTTP transport. The StreamableHTTP transport provides better performance, standards compliance, and simplified architecture compared to the previous SSE implementation.

## Features Demonstrated

### 🚀 **StreamableHTTP Transport**
- Single endpoint (`/mcp`) for all MCP communication
- Built-in session management and connection pooling
- Automatic error handling and recovery
- Standards-compliant HTTP streaming

### 🛠️ **MCP Tools**
- `get_weather`: Get weather information for cities
- `calculate_math`: Perform mathematical calculations safely
- `generate_password`: Generate secure random passwords
- `list_todos`: List and filter todo items

### 📚 **MCP Resources**
- `config://app/{section}`: Get application configuration
- `docs://api/{endpoint}`: Get API documentation
- `logs://recent/{hours}`: Get recent application logs

### 📝 **MCP Prompts**
- `code-review`: Generate code review prompt templates
- `api-documentation`: Generate API documentation prompts

## Architecture

```
Client Request → Azure Functions → MCPFunctionApp → StreamableHTTP Transport → MCP Protocol
                                                  ↓
                                            Tools/Resources/Prompts
```

### Key Components

1. **MCPFunctionApp**: Main application class that integrates with Azure Functions
2. **StreamableHTTPSessionManager**: Manages HTTP streaming and session lifecycle
3. **MCP Protocol Handlers**: Handle tools, resources, and prompts via FastMCP decorators

## Getting Started

### Prerequisites

- Python 3.10 or later
- Azure Functions Core Tools 4.x
- Azure CLI (optional, for deployment)

### Local Development

1. **Clone and Navigate**:
   ```bash
   git clone <repository>
   cd samples/mcp_streamable_http_sample
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Function App**:
   ```bash
   func start
   ```

4. **Test the Health Endpoint**:
   ```bash
   curl http://localhost:7071/api/health
   ```

### MCP Client Integration

The MCP server exposes a single endpoint that handles all MCP protocol communication:

**Endpoint**: `POST http://localhost:7071/api/mcp`

#### Example MCP Requests

1. **List Available Tools**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/list"
   }
   ```

2. **Call the Weather Tool**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 2,
     "method": "tools/call",
     "params": {
       "name": "get_weather",
       "arguments": {
         "location": "New York",
         "units": "celsius"
       }
     }
   }
   ```

3. **Get a Resource**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 3,
     "method": "resources/read",
     "params": {
       "uri": "config://app/database"
     }
   }
   ```

4. **Get a Prompt**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 4,
     "method": "prompts/get",
     "params": {
       "name": "code-review",
       "arguments": {
         "language": "python",
         "style": "security"
       }
     }
   }
   ```

### Testing with curl

#### Health Check
```bash
curl http://localhost:7071/api/health
```

#### MCP Protocol Test
```bash
curl -X POST http://localhost:7071/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

#### Weather Tool Test
```bash
curl -X POST http://localhost:7071/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {
        "location": "Tokyo",
        "units": "fahrenheit"
      }
    }
  }'
```

## StreamableHTTP vs SSE Comparison

### Previous SSE Implementation
- Required 2 separate endpoints (`/sse` and `/messages`)
- Manual stream management
- Custom SSE implementation
- Limited error recovery

### New StreamableHTTP Implementation
- Single endpoint (`/mcp`) handles all communication
- Automatic session management
- Standards-compliant HTTP streaming
- Built-in error handling and recovery
- Better performance and connection pooling

## Configuration

### Environment Variables

Set these in `local.settings.json` for local development or in Azure Function App settings for production:

```json
{
  "FUNCTIONS_WORKER_RUNTIME": "python",
  "PYTHON_ENABLE_INIT_INDEXING": "1",
  "PYTHON_ENABLE_WORKER_EXTENSIONS": "1"
}
```

### Authentication

The sample uses `AuthLevel.ANONYMOUS` for demonstration purposes. For production, use:

```python
app = MCPFunctionApp(
    auth_level=func.AuthLevel.FUNCTION,  # Requires function key
    # or
    auth_level=func.AuthLevel.ADMIN,     # Requires admin key
)
```

## Deployment to Azure

1. **Create a Function App**:
   ```bash
   az functionapp create \
     --resource-group myResourceGroup \
     --consumption-plan-location eastus \
     --runtime python \
     --runtime-version 3.11 \
     --functions-version 4 \
     --name myMCPServer
   ```

2. **Deploy the Function**:
   ```bash
   func azure functionapp publish myMCPServer
   ```

3. **Configure Application Settings**:
   ```bash
   az functionapp config appsettings set \
     --name myMCPServer \
     --resource-group myResourceGroup \
     --settings "PYTHON_ENABLE_INIT_INDEXING=1" "PYTHON_ENABLE_WORKER_EXTENSIONS=1"
   ```

## Advanced Features

### Session Management

The StreamableHTTP transport supports both stateful and stateless modes:

```python
# Stateful (default) - enables session tracking and connection reuse
StreamableHTTPSessionManager(
    app=self._mcp_server,
    stateless=False
)

# Stateless - creates fresh transport for each request
StreamableHTTPSessionManager(
    app=self._mcp_server,
    stateless=True
)
```

### Event Store (Resumability)

For production deployments, you can implement an event store for resumable connections:

```python
from mcp.server.streamable_http import EventStore

class AzureEventStore(EventStore):
    """Custom event store using Azure Storage or Cosmos DB"""
    # Implement event storage methods
    pass

session_manager = StreamableHTTPSessionManager(
    app=self._mcp_server,
    event_store=AzureEventStore()
)
```

### Security Settings

Configure transport security for production:

```python
from mcp.server.transport_security import TransportSecuritySettings

security_settings = TransportSecuritySettings(
    allowed_origins=["https://myapp.com"],
    require_tls=True
)

session_manager = StreamableHTTPSessionManager(
    app=self._mcp_server,
    security_settings=security_settings
)
```

## Monitoring and Logging

The sample includes comprehensive logging:

```python
import logging
logger = logging.getLogger(__name__)

# All tool/resource/prompt calls are logged
@app.tool()
def my_tool(param: str) -> str:
    logger.info(f"Tool called with param: {param}")
    # ... tool implementation
```

Monitor the function app using:
- Azure Application Insights
- Azure Function App logs
- Custom metrics and telemetry

## Troubleshooting

### Common Issues

1. **Function not responding**:
   - Check if `PYTHON_ENABLE_INIT_INDEXING=1` is set
   - Verify Azure Functions Core Tools version (4.x required)

2. **MCP protocol errors**:
   - Ensure request has proper JSON-RPC 2.0 format
   - Check Content-Type header is `application/json`

3. **Tool/Resource not found**:
   - Verify the tool/resource is properly decorated
   - Check function app logs for registration errors

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- The StreamableHTTP transport automatically manages connection pooling
- Session management reduces overhead for multiple requests
- Consider using stateless mode for serverless environments with intermittent traffic
- Use event store for high-availability scenarios requiring resumability

## Contributing

To extend this sample:

1. Add new tools using the `@app.tool()` decorator
2. Add new resources using the `@app.resource()` decorator
3. Add new prompts using the `@app.prompt()` decorator
4. Implement custom event stores for advanced scenarios
5. Add authentication and authorization logic as needed

## License

This sample is provided under the MIT license. See the main repository for full license details.
