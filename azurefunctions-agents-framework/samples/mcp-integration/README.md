# MCP Integration with Azure Functions Agents

This directory contains examples of integrating Model Context Protocol (MCP) servers with Azure Functions agents using the Azure Functions Agent Framework.

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that enables AI applications to securely access external tools and data sources. MCP servers provide tools that agents can use to extend their capabilities.

## Examples Structure

Each example is organized in its own directory with complete setup instructions, dependencies, and documentation:

```
mcp-integration/
├── weather-agent/          # Weather MCP integration example
│   ├── weather_mcp_agent.py
│   ├── README.md
│   ├── requirements.txt
│   ├── host.json
│   └── local.settings.json.template
├── git-agent/              # Git repository analysis example
│   ├── git_agent.py
│   ├── README.md
│   ├── requirements.txt
│   ├── host.json
│   └── local.settings.json.template
├── sse-integration/        # SSE MCP server and client example
│   ├── sse_server.py
│   ├── sse_agent.py
│   ├── README.md
│   ├── requirements.txt
│   ├── host.json
│   └── local.settings.json.template
├── test_examples.py        # Validation script for all examples
└── requirements.txt        # Common dependencies
```

## Examples Overview

### 1. Weather Agent (`weather-agent/`)

A comprehensive example showing how to integrate with a weather MCP server to provide weather information through natural language interactions.

**Key Features:**
- Weather information retrieval for any location
- Type-safe MCP server configuration using `MCPServerStdioParams`
- Robust error handling for network and API issues
- Ready for Azure Functions deployment

**Quick Start:**
```bash
cd weather-agent/
pip install -r requirements.txt
cp local.settings.json.template local.settings.json
# Edit local.settings.json with your OpenAI API key
func start
```

### 2. Git Repository Agent (`git-agent/`)

Demonstrates integration with a Git MCP server for repository analysis and operations.

**Key Features:**
- Git repository analysis and insights
- File listing, content reading, and git operations
- Support for both local and remote Git MCP servers
- Intelligent code structure analysis

**Quick Start:**
```bash
cd git-agent/
pip install -r requirements.txt
cp local.settings.json.template local.settings.json
# Edit local.settings.json with your OpenAI API key
func start
```

### 3. SSE MCP Integration (`sse-integration/`)

A complete Server-Sent Events (SSE) based MCP implementation with both server and client components.

**Key Features:**
- FastAPI-based SSE MCP server with multiple demonstration tools
- Azure Functions agent with automatic server lifecycle management
- Real-time bidirectional communication using SSE and HTTP
- Tools for echo, calculation, time operations, and more

**Quick Start:**
```bash
cd sse-integration/
pip install -r requirements.txt
cp local.settings.json.template local.settings.json
# Edit local.settings.json with your OpenAI API key
func start
```

## Getting Started

### Prerequisites

- Python 3.8+
- Azure Functions Core Tools
- OpenAI API key (or compatible LLM provider)
- Node.js (for some MCP servers)

### Common Setup Steps

1. **Choose an Example**: Navigate to the example directory you want to try
2. **Install Dependencies**: Run `pip install -r requirements.txt` in the example directory
3. **Configure Settings**: Copy and edit the `local.settings.json.template` file
4. **Run Locally**: Execute `func start` to run the Azure Function locally
5. **Test the Agent**: Use curl or a REST client to send chat messages

### Example Request Format

All examples accept POST requests with this format:

```bash
curl -X POST "http://localhost:7071/api/{function_name}" \
     -H "Content-Type: application/json" \
     -d '{"message": "Your question here"}'
```

## MCP Server Types Supported

The Azure Functions Agent Framework supports three types of MCP server connections:

### 1. STDIO (Standard Input/Output)
- Uses process spawning and pipe communication
- Ideal for local MCP servers and command-line tools
- Example: Weather agent using npm-installed weather server

### 2. SSE (Server-Sent Events)
- Uses HTTP-based communication with Server-Sent Events
- Perfect for web-based MCP servers and real-time applications
- Example: SSE integration with FastAPI server

### 3. Streamable HTTP
- Uses standard HTTP requests and responses
- Best for REST API-style MCP servers
- Example: Git agent connecting to HTTP-based git server

## Validation

Use the provided test script to validate all examples:

```bash
python test_examples.py
```

This script checks:
- Python syntax and compilation
- Import dependencies
- Configuration file validity
- Example completeness

## Deployment to Azure

Each example includes the necessary configuration files for Azure Functions deployment:

```bash
cd {example-directory}/
func azure functionapp publish <your-function-app-name>
```

## Key Framework Features Demonstrated

- **Type Safety**: All examples use proper type annotations and MCP parameter objects
- **Error Handling**: Comprehensive error handling for MCP communication failures
- **Lifecycle Management**: Proper server startup, health checks, and cleanup
- **Flexibility**: Support for different MCP server types and communication patterns
- **Azure Integration**: Full compatibility with Azure Functions hosting and scaling

## Contributing

When adding new MCP integration examples:

1. Create a new directory under `mcp-integration/`
2. Include all necessary files (agent code, README, requirements, configs)
3. Follow the established patterns for error handling and type safety
4. Update this main README to include your example
5. Add tests to `test_examples.py`

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [Azure Functions Agent Framework](../../README.md)
- [MCP Server Registry](https://github.com/modelcontextprotocol/servers)
