# Git MCP Server Function App Test

This directory contains a test Azure Function App that uses the git MCP server to demonstrate the HTTP-to-STDIO bridge functionality.

## Setup

1. Create a virtual environment:
   ```bash
   cd function_app_test
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies (including editable package):
   ```bash
   pip install -e ..  # Install the mcp-stdio-adapter as editable
   pip install azure-functions azure-functions-core-tools
   ```

3. Install the git MCP server:
   ```bash
   uvx install mcp-server-git
   ```

## Running the Function App

1. Start the Azure Functions runtime:
   ```bash
   func start
   ```

2. The function app will be available at:
   - Main MCP endpoint: `http://localhost:7071/api/mcp`
   - Health check: `http://localhost:7071/api/health`
   - Info endpoint: `http://localhost:7071/api/info`

## Testing the MCP Server

You can test the MCP server by sending JSON-RPC requests to the `/api/mcp` endpoint:

### Example: List available tools
```bash
curl -X POST http://localhost:7071/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### Example: Get repository status
```bash
curl -X POST http://localhost:7071/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "git_status",
      "arguments": {}
    }
  }'
```

## Configuration

- The git repository path is set to "." (current directory) by default
- You can change the `GIT_REPO_PATH` in `local.settings.json` or in the function app configuration
- The MCP server uses `uvx mcp-server-git` to run the git MCP server

## Troubleshooting

1. Make sure you're in a git repository when testing
2. Ensure `mcp-server-git` is installed and accessible via `uvx`
3. Check the Azure Functions logs for any connection issues
4. Use the health endpoint to verify the MCP server status
