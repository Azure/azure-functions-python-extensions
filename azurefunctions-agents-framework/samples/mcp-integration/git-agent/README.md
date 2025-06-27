# Git MCP Agent Example

This example demonstrates how to create an Azure Functions agent that integrates with a Git MCP server to analyze and interact with Git repositories.

## Features

- **Repository Analysis**: Analyze Git repositories (local or remote)
- **Git Operations**: List files, read content, check git status, view commit history
- **Smart Integration**: Automatically detects and uses available Git MCP servers
- **Type-Safe MCP Integration**: Uses the Azure Functions Agent Framework's MCP support
- **Flexible Deployment**: Supports both local Git repos and HTTP-accessible Git servers

## Prerequisites

- Python 3.8+
- Azure Functions Core Tools (for local development)
- OpenAI API key
- Git installed locally (for local repository analysis)
- Access to a Git MCP server (local or remote)

## Setup

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:

   ```bash
   cp local.settings.json.template local.settings.json
   # Edit local.settings.json with your API keys and Git server settings
   ```

3. **Set Environment Variables**:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `GIT_MCP_SERVER_URL`: URL of your Git MCP server (optional, defaults to local)

## Usage

### Local Development

1. **Start the Function App**:

   ```bash
   func start
   ```

2. **Test the Git Agent**:

   ```bash
   curl -X POST "http://localhost:7071/api/git_chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "Analyze the repository structure", "repository_path": "/path/to/your/repo"}'
   ```

### Sample Interactions

- "What files are in this repository?"
- "Show me the recent commit history"
- "What's the current git status?"
- "Analyze the code structure in src/"
- "Find all Python files in the project"

## Code Structure

- `git_agent.py`: Main Azure Function with Git MCP integration
- `host.json`: Azure Functions host configuration
- `local.settings.json.template`: Template for local environment variables
- `requirements.txt`: Python dependencies

## Deployment

Deploy to Azure Functions using:

```bash
func azure functionapp publish <your-function-app-name>
```

## How It Works

1. The Azure Function receives a chat message with an optional repository path
2. Creates an MCP server connection to the Git service
3. Uses the agent framework to process Git-related requests
4. Returns analysis, file listings, or other Git information

## MCP Server Setup

### Local Git MCP Server

If you want to run a local Git MCP server:

```bash
# Clone and setup a Git MCP server
git clone https://github.com/modelcontextprotocol/servers.git
cd servers/src/git
pip install -e .
```

### Remote Git MCP Server

Configure the `GIT_MCP_SERVER_URL` environment variable to point to your remote Git MCP server.

## Customization

- **Repository Sources**: Add support for GitHub, GitLab, or other Git hosting services
- **Advanced Git Operations**: Add support for diffs, merges, branch operations
- **Security**: Add authentication and access control for repository access
- **Caching**: Add caching for repository metadata and file contents
