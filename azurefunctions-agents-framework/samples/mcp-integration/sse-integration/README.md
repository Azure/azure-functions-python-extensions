# SSE MCP Integration Example

This example demonstrates how to create both an SSE-based MCP server and an Azure Functions agent that communicates with it using Server-Sent Events.

## Features

- **SSE MCP Server**: A FastAPI-based MCP server that communicates via Server-Sent Events
- **Agent Integration**: Azure Functions agent that starts and manages the SSE MCP server
- **Real-time Communication**: Bidirectional communication using SSE and HTTP
- **Lifecycle Management**: Automatic server startup, health checking, and cleanup
- **Tool Demonstrations**: Sample tools for echo, calculation, and time operations

## Prerequisites

- Python 3.8+
- Azure Functions Core Tools (for local development)
- OpenAI API key
- Available ports for the SSE server (default: 8001)

## Setup

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:

   ```bash
   cp local.settings.json.template local.settings.json
   # Edit local.settings.json with your API keys
   ```

3. **Set Environment Variables**:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SSE_SERVER_PORT`: Port for the SSE server (optional, defaults to 8001)

## Components

### SSE Server (`sse_server.py`)

A standalone FastAPI server that implements the MCP protocol over SSE:

- **Echo Tool**: Simple echo functionality for testing
- **Calculator Tool**: Basic arithmetic operations
- **Time Tool**: Current time retrieval
- **Health Endpoint**: Server health monitoring

### SSE Agent (`sse_agent.py`)

An Azure Functions agent that:

- Starts the SSE MCP server automatically
- Manages server lifecycle (startup, health checks, cleanup)
- Processes chat requests using MCP tools
- Handles server communication errors gracefully

## Usage

### Local Development

1. **Start the Function App**:

   ```bash
   func start
   ```

   The function will automatically start the SSE server on port 8001.

2. **Test the SSE Agent**:

   ```bash
   # Test echo functionality
   curl -X POST "http://localhost:7071/api/sse_chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "Echo: Hello, SSE MCP!"}'

   # Test calculator
   curl -X POST "http://localhost:7071/api/sse_chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "Calculate 15 + 27"}'

   # Test time
   curl -X POST "http://localhost:7071/api/sse_chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "What time is it?"}'
   ```

3. **Monitor SSE Server**:

   ```bash
   # Check server health
   curl http://localhost:8001/health
   ```

### Manual Server Testing

You can also run the SSE server independently:

```bash
python sse_server.py
```

## Code Structure

- `sse_server.py`: FastAPI-based SSE MCP server implementation
- `sse_agent.py`: Azure Functions agent with SSE MCP integration
- `host.json`: Azure Functions host configuration
- `local.settings.json.template`: Template for local environment variables
- `requirements.txt`: Python dependencies

## Deployment

Deploy to Azure Functions using:

```bash
func azure functionapp publish <your-function-app-name>
```

**Note**: For production deployment, consider running the SSE server as a separate service and configuring the agent to connect to it.

## How It Works

### Server-Sent Events Flow

1. **Server Startup**: The agent starts the SSE MCP server on a local port
2. **Health Check**: Verifies the server is ready to accept connections
3. **SSE Connection**: Establishes an SSE connection for receiving messages
4. **Tool Execution**: Sends tool requests via HTTP POST to the server
5. **Response Handling**: Processes responses and manages errors
6. **Cleanup**: Properly shuts down the server when done

### MCP Protocol over SSE

- **Initialize**: Standard MCP initialization handshake
- **List Tools**: Discover available tools from the server
- **Call Tools**: Execute tools with parameters and receive results
- **Error Handling**: Robust error handling for network and protocol issues

## Sample Interactions

- "Echo: Hello, World!" → Server echoes the message
- "Calculate 25 * 4" → Server performs calculation and returns result
- "What's the current time?" → Server returns current timestamp
- "Add 100 and 50" → Server performs addition

## Customization

- **Add New Tools**: Extend the SSE server with additional MCP tools
- **Authentication**: Add API key or token-based authentication
- **Scaling**: Deploy the SSE server separately for production use
- **Monitoring**: Add logging and monitoring for the SSE communication
- **Error Recovery**: Implement automatic server restart on failures

## Troubleshooting

- **Port Conflicts**: Change `SSE_SERVER_PORT` if port 8001 is in use
- **Server Startup**: Check logs if the SSE server fails to start
- **Connection Issues**: Verify firewall settings and port accessibility
- **Tool Errors**: Check the SSE server logs for tool execution issues
