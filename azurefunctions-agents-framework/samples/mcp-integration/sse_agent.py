#!/usr/bin/env python3
"""
SSE Agent with MCP Integration Example

This example demonstrates how to integrate an SSE (Server-Sent Events) MCP server
with an Azure Functions agent. It starts a local SSE MCP server and connects to it.

To run this example:
1. Set your OpenAI API key in environment variables
2. Deploy to Azure Functions or run locally

For local testing:
    func start

The example will automatically start the SSE server at http://localhost:8000/sse
and connect to it.

Example request:
    POST /api/sse_agent
    {
        "messages": [
            {"role": "user", "content": "Add these numbers: 15 and 27"}
        ]
    }
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from typing import Any, List, Optional

import azure.functions as func
from azurefunctions.agents import (
    Agent,
    AgentFunctionApp,
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MCPServer,
    MCPServerMode,
    MCPServerSseParams,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to track the SSE server process
sse_server_process: Optional[subprocess.Popen] = None


def start_sse_server() -> subprocess.Popen:
    """Start the SSE MCP server as a subprocess."""
    global sse_server_process
    
    if sse_server_process and sse_server_process.poll() is None:
        logger.info("SSE server already running")
        return sse_server_process
    
    try:
        # Get the path to the server file
        this_dir = os.path.dirname(os.path.abspath(__file__))
        server_file = os.path.join(this_dir, "sse_server.py")
        
        if not os.path.exists(server_file):
            raise FileNotFoundError(f"SSE server file not found: {server_file}")
        
        logger.info("Starting SSE server at http://localhost:8000/sse ...")
        
        # Start the server process
        sse_server_process = subprocess.Popen(
            ["python", server_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start
        time.sleep(3)
        
        # Check if process is still running
        if sse_server_process.poll() is not None:
            stdout, stderr = sse_server_process.communicate()
            raise RuntimeError(f"SSE server failed to start. Error: {stderr}")
        
        logger.info("SSE server started successfully")
        return sse_server_process
        
    except Exception as e:
        logger.error(f"Failed to start SSE server: {e}")
        raise


def stop_sse_server():
    """Stop the SSE MCP server."""
    global sse_server_process
    
    if sse_server_process:
        try:
            sse_server_process.terminate()
            sse_server_process.wait(timeout=5)
            logger.info("SSE server stopped")
        except subprocess.TimeoutExpired:
            sse_server_process.kill()
            logger.warning("SSE server forcefully killed")
        except Exception as e:
            logger.error(f"Error stopping SSE server: {e}")
        finally:
            sse_server_process = None


async def handle_sse_request(messages: List[ChatMessage], llm_config: LLMConfig) -> ChatMessage:
    """Handle requests using SSE MCP integration."""
    
    # Ensure SSE server is running
    start_sse_server()
    
    # Create MCP server for SSE tools
    sse_mcp = MCPServer(
        name="sse-demo-tools",
        mode=MCPServerMode.SSE,
        params=MCPServerSseParams(
            url="http://localhost:8000/sse",
            timeout=10.0,
            sse_read_timeout=30.0
        ),
        cache_tools_list=True,  # Cache tools for better performance
    )
    
    # Create agent with MCP integration
    agent = Agent(
        name="SSEAgent",
        instructions="""You are a helpful assistant with access to various utility tools via SSE MCP server.
        
        You have access to the following tools:
        - Mathematical operations (add, multiply, factorial)
        - Random data generation (secret words, UUIDs)
        - Weather information (current weather for cities)
        - System information
        
        Use these tools to help answer user questions. Always be specific about what calculations
        or operations you're performing and show your work when doing mathematical operations.""",
        llm_config=llm_config,
        mcp_servers=[sse_mcp],
    )
    
    # Get response from agent
    response = await agent.run(messages=messages)
    return response


# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)

# Create the SSE agent
sse_agent = Agent(
    name="SSEAgent",
    instructions="""You are a helpful assistant with access to various utility tools via SSE MCP server.
    
    You have access to tools for:
    - Mathematical operations (add, multiply, factorial calculations)
    - Random data generation (secret words, UUIDs)
    - Weather information (current weather for cities)
    - System information
    
    Use these tools to help answer user questions. Always be specific about what calculations
    or operations you're performing and show your work when doing mathematical operations.""",
    llm_config=llm_config,
    mcp_servers=[
        MCPServer(
            name="sse-demo-tools",
            mode=MCPServerMode.SSE,
            params=MCPServerSseParams(
                url="http://localhost:8000/sse",
                timeout=10.0,
                sse_read_timeout=30.0
            ),
            cache_tools_list=True,
        )
    ],
)

# Create Function App with the SSE agent
app = AgentFunctionApp(agents={"SSEAgent": sse_agent})


@app.function_name("startup")
@app.timer_trigger(schedule="0 */30 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False)
async def startup_function(timer):
    """Startup function to ensure SSE server is running."""
    try:
        start_sse_server()
        logger.info("SSE server startup check completed")
    except Exception as e:
        logger.error(f"Failed to start SSE server during startup: {e}")


@app.route(route="sse_agent", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def sse_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for SSE MCP agent."""
    
    try:
        # Parse request
        req_body = req.get_json()
        if not req_body or "messages" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request format. Expected 'messages' field."}),
                status_code=400,
                mimetype="application/json"
            )
        
        messages = [ChatMessage(**msg) for msg in req_body["messages"]]
        
        # Get response from the SSE agent
        response = await handle_sse_request(messages, llm_config)
        
        return func.HttpResponse(
            json.dumps({
                "response": response.content,
                "role": response.role,
                "server_url": "http://localhost:8000/sse"
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in SSE agent: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="sse_health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def sse_health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for SSE agent."""
    
    # Check if SSE server is running
    server_running = sse_server_process and sse_server_process.poll() is None
    
    # Try to start server if not running
    if not server_running:
        try:
            start_sse_server()
            server_running = True
        except Exception as e:
            logger.error(f"Failed to start SSE server: {e}")
    
    return func.HttpResponse(
        json.dumps({
            "status": "healthy" if server_running else "degraded",
            "agent": "SSEAgent",
            "mcp_integration": "enabled",
            "sse_server": "running" if server_running else "not_running",
            "server_url": "http://localhost:8000/sse"
        }),
        status_code=200 if server_running else 503,
        mimetype="application/json"
    )


@app.route(route="stop_sse_server", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def stop_server_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint to manually stop the SSE server."""
    
    try:
        stop_sse_server()
        return func.HttpResponse(
            json.dumps({"message": "SSE server stopped successfully"}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"Failed to stop SSE server: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


if __name__ == "__main__":
    # For local testing
    import asyncio
    import atexit
    
    # Register cleanup function
    atexit.register(stop_sse_server)
    
    async def test_agent():
        """Test the agent locally."""
        
        try:
            # Start the SSE server
            start_sse_server()
            
            # Test different tools
            test_cases = [
                "Add these numbers: 7 and 22",
                "What's the weather in Tokyo?",
                "What's the secret word?",
                "Calculate the factorial of 5",
                "Generate a UUID for me",
                "What's the system information?"
            ]
            
            for i, question in enumerate(test_cases, 1):
                print(f"\n{'-' * 50}")
                print(f"Test {i}: {question}")
                print("-" * 50)
                
                messages = [ChatMessage(role="user", content=question)]
                
                try:
                    response = await handle_sse_request(messages, llm_config)
                    print(f"Agent response: {response.content}")
                except Exception as e:
                    print(f"Test failed: {e}")
            
        except Exception as e:
            print(f"Test setup failed: {e}")
            print("Make sure the sse_server.py file is in the same directory")
            print("and that you have the required dependencies installed:")
            print("  pip install mcp requests")
        
        finally:
            # Clean up
            stop_sse_server()
    
    asyncio.run(test_agent())
