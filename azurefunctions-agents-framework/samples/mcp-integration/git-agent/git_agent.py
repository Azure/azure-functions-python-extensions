#!/usr/bin/env python3
"""
Git Agent with MCP Integration Example

This example demonstrates how to integrate a Git MCP server with an Azure Functions agent.
The agent can analyze git repositories, provide commit history, contributor information,
and answer questions about the codebase.

To run this example:
1. Install the git MCP server: pip install mcp-server-git or uvx mcp-server-git
2. Set your OpenAI API key in environment variables
3. Deploy to Azure Functions or run locally

For local testing:
    func start

Example request:
    POST /api/git_agent
    {
        "messages": [
            {"role": "user", "content": "Who are the most frequent contributors to this repository?"}
        ],
        "repo_path": "/path/to/your/git/repository"
    }
"""

import asyncio
import json
import logging
import os
import shutil
from typing import List

import azure.functions as func

from azurefunctions.agents import (
    Agent,
    AgentFunctionApp,
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MCPServer,
    MCPServerMode,
    MCPServerStdioParams,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_git_request(
    messages: List[ChatMessage], llm_config: LLMConfig, repo_path: str
) -> ChatMessage:
    """Handle git repository analysis request using MCP integration."""

    # Check if git MCP server is available
    if not shutil.which("uvx") and not shutil.which("mcp-server-git"):
        raise RuntimeError(
            "Git MCP server not found. Please install with: pip install mcp-server-git"
        )

    # Use uvx if available, otherwise assume mcp-server-git is in PATH
    command = "uvx" if shutil.which("uvx") else "mcp-server-git"
    args = ["mcp-server-git"] if command == "uvx" else []

    # Create MCP server for git tools
    git_mcp = MCPServer(
        name="git-tools",
        mode=MCPServerMode.STDIO,
        params=MCPServerStdioParams(
            command=command, args=args, env={"GIT_REPO_PATH": repo_path}
        ),
        cache_tools_list=True,  # Cache tools for better performance
    )

    # Create agent with MCP integration
    agent = Agent(
        name="GitAgent",
        instructions=f"""You are a helpful git repository analyst. Use the available git tools
        to analyze the repository at {repo_path}. You can:

        - Analyze commit history and patterns
        - Identify top contributors
        - Examine code changes and diffs
        - Provide insights about repository structure
        - Answer questions about the codebase evolution

        Always use the repo_path parameter as: {repo_path}

        Provide detailed analysis with specific data points when possible.""",
        llm_config=llm_config,
        mcp_servers=[git_mcp],
    )

    # Get response from agent
    response = await agent.run(messages=messages)
    return response


# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3,  # Lower temperature for more factual analysis
)

# Create the git agent
git_agent = Agent(
    name="GitAgent",
    instructions="""You are a helpful git repository analyst. Use the available git tools
    to analyze repositories and provide insights about code, contributors, and development patterns.

    You can help with:
    - Analyzing commit history and patterns
    - Identifying top contributors
    - Examining code changes and diffs
    - Providing insights about repository structure
    - Answering questions about codebase evolution

    Always provide detailed analysis with specific data points when possible.""",
    llm_config=llm_config,
    mcp_servers=[
        MCPServer(
            name="git-tools",
            mode=MCPServerMode.STDIO,
            params=MCPServerStdioParams(
                command="uvx" if shutil.which("uvx") else "mcp-server-git",
                args=["mcp-server-git"] if shutil.which("uvx") else [],
            ),
            cache_tools_list=True,
        )
    ],
)

# Create Function App with the git agent
app = AgentFunctionApp(agents={"GitAgent": git_agent})


@app.route(route="git_agent", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def git_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for git repository analysis agent."""

    try:
        # Parse request
        req_body = req.get_json()
        if not req_body or "messages" not in req_body:
            return func.HttpResponse(
                json.dumps(
                    {"error": "Invalid request format. Expected 'messages' field."}
                ),
                status_code=400,
                mimetype="application/json",
            )

        # Get repository path from request or environment
        repo_path = req_body.get("repo_path") or os.getenv("GIT_REPO_PATH", "/tmp/repo")

        if not os.path.exists(repo_path) or not os.path.exists(
            os.path.join(repo_path, ".git")
        ):
            return func.HttpResponse(
                json.dumps(
                    {
                        "error": f"Invalid git repository path: {repo_path}. "
                        "Please provide a valid git repository path in 'repo_path' field "
                        "or set GIT_REPO_PATH environment variable."
                    }
                ),
                status_code=400,
                mimetype="application/json",
            )

        messages = [ChatMessage(**msg) for msg in req_body["messages"]]

        # Get response from the git agent
        response = await handle_git_request(messages, llm_config, repo_path)

        return func.HttpResponse(
            json.dumps(
                {
                    "response": response.content,
                    "role": response.role,
                    "repo_path": repo_path,
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error in git agent: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="git_health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def git_health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for git agent."""

    # Check if git MCP server is available
    git_available = bool(shutil.which("uvx") or shutil.which("mcp-server-git"))

    return func.HttpResponse(
        json.dumps(
            {
                "status": "healthy" if git_available else "degraded",
                "agent": "GitAgent",
                "mcp_integration": "enabled",
                "git_server": "available" if git_available else "not_found",
                "dependencies": {
                    "uvx": bool(shutil.which("uvx")),
                    "mcp-server-git": bool(shutil.which("mcp-server-git")),
                },
            }
        ),
        status_code=200 if git_available else 503,
        mimetype="application/json",
    )


if __name__ == "__main__":
    # For local testing
    import asyncio

    async def test_agent():
        """Test the agent locally."""

        # Ask user for repository path
        repo_path = input("Please enter the path to the git repository: ").strip()

        if not os.path.exists(repo_path) or not os.path.exists(
            os.path.join(repo_path, ".git")
        ):
            print(f"Error: {repo_path} is not a valid git repository")
            return

        messages = [
            ChatMessage(
                role="user",
                content="Who are the most frequent contributors to this repository?",
            )
        ]

        try:
            response = await handle_git_request(messages, llm_config, repo_path)
            print(f"\nAgent response: {response.content}")

            # Ask another question
            messages = [
                ChatMessage(
                    role="user", content="Summarize the last change in the repository."
                )
            ]

            response = await handle_git_request(messages, llm_config, repo_path)
            print(f"\nAgent response: {response.content}")

        except Exception as e:
            print(f"Test failed: {e}")
            print("Note: This example requires the git MCP server to be installed.")
            print("Run: pip install mcp-server-git")
            print("Or with uvx: pip install uvx")

    asyncio.run(test_agent())
