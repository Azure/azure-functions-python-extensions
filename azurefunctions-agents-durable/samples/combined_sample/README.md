# Combined Agents with Durable Orchestrator Sample

This sample demonstrates how to use the Azure Functions Agents Durable framework to create and call both HTTP and MCP agents from a single Durable Functions orchestrator.

## Sample Overview

This combined sample includes:

1. **HTTP Agent** - Simple Hello World functions exposed via HTTP endpoints
2. **MCP Server** - A Model Context Protocol server exposing tools
3. **Durable Orchestrator** - A Durable Functions orchestrator that calls both agents

All three components are combined into a single function app for simplicity.

## Prerequisites

- Python 3.8 or later
- Azure Functions Core Tools v4
- Azure Storage Emulator or Azure Storage Account

## Setup & Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Configure your Azure OpenAI settings in `local.settings.json` if you're planning to use AI capabilities.

3. Start the Function App:

```bash
func start
```

## How It Works

### HTTP Agent

The sample includes two simple HTTP endpoints:

- `/api/hello_world` - Returns "Hello, World!"
- `/api/hello_name` - Takes a name parameter and returns a personalized greeting

These endpoints are registered as an HTTP agent named "hello_world_agent" in the Durable Agents framework.

### MCP Server

The sample includes an MCP tool:

- `hello_mcp` - Takes a user name parameter and returns a greeting

The MCP server is registered as an MCP agent named "mcp_agent" in the Durable Agents framework.

### Durable Orchestrator

The sample includes a durable orchestrator that:

1. Calls the Hello World agent via HTTP
2. Calls the MCP agent via the MCP protocol
3. Also demonstrates calling an MCP tool directly via an activity function
4. Returns all responses in a combined result

## Testing the Sample

1. Start the orchestrator by sending a request:

```
GET http://localhost:7071/api/start_orchestration?name=YourName
```

2. Use the returned instance ID to check the status:

```
GET http://localhost:7071/api/orchestrator_status/{instance_id}
```

3. The orchestration result will include responses from both agents.

## Key Concepts Demonstrated

1. **Context-First Parameter Pattern** - All agent calls use the `context` parameter as the first argument
2. **Agent Registration** - Both HTTP and MCP agents are registered with the framework
3. **Multiple Agent Types** - A single orchestrator calls multiple agent types
4. **MCP Integration** - Direct and framework-based MCP tool calls

## Code Structure

- `function_app.py` - Contains all function code divided into sections
  - Part 1: Hello World Agent Definition
  - Part 2: MCP Server Definition
  - Part 3: Durable Orchestrator
  - Part 4: HTTP Triggers
- `host.json` - Function app configuration
- `local.settings.json` - Environment settings
- `requirements.txt` - Package dependencies
