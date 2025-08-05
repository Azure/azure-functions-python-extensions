"""
Combined Sample: Durable Orchestrator calling both Hello World Agent and MCP Server
This demonstrates how to use the azure-functions-agents-durable framework to call different agent types
"""

# Apply the import patch to fix azurefunctions.agents imports
import patch_imports
patch_imports.apply_patch()

import json
import logging
import os
from typing import Dict, Any

import azure.functions as func
from azure.functions import AuthLevel

import azure.durable_functions as df
from azurefunctions.agents.durable import (
    DFAgentFramework, AgentCaller, AgentConfig, CallMode, orchestrator
)
from azurefunctions.agent import AgentFunctionApp, MCPServerStdio, LLMConfig, LLMProvider

# Create the Function app and setup the agent framework
app = df.DFApp()
framework = DFAgentFramework(app)

#########################################
# PART 1: Hello World Agent Definition
#########################################

@app.route(route="hello_world", auth_level=func.AuthLevel.ANONYMOUS)
def hello_world_http(req: func.HttpRequest) -> func.HttpResponse:
    """Simple HTTP endpoint that returns Hello, World!"""
    return func.HttpResponse("Hello, World!")

@app.route(route="hello_name", auth_level=func.AuthLevel.ANONYMOUS)
def hello_name_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint that greets a person by name"""
    name = req.params.get('name', req.get_json().get('name', 'Anonymous') if req.get_body() else 'Anonymous')
    return func.HttpResponse(f"Hello, {name}! Nice to meet you!")

from azurefunctions.agents import AgentFunctionApp, MCPServerStdio

# Create Git MCP server based on your JSON configuration
git_mcp_server = MCPServerStdio(
    params={
        "command":"uvx",  # Command from the JSON config
        "args":["mcp-server-git"]  # Args array from JSON
    },
    name="git"  # Server name from the JSON key
)

# Create the Hello World Agent Function App
 
# Configure LLM for conversational AI
llm_config = LLMConfig(
    provider=LLMProvider.AzureOpenAI,
    model_name="gpt-4o",  # Using a cost-effective model
    temperature=0.7,
    max_tokens=1000,
    # API key will be read from OPENAI_API_KEY environment variable
    # Or you can set it explicitly: api_key="your-api-key-here"
)
 
# TODO What is the agent_mode? 
helloAgent = AgentFunctionApp(
    name="hello_world_agent",
    instructions="Say hello to the user",
    mcp_servers=[git_mcp_server],  # Conditional MCP
    http_auth_level=AuthLevel.ANONYMOUS,  # For easier testing - change for production
    llm_config=llm_config,
    enable_conversational_agent=True,
    version="1.0.0",
    description="A helpful weather assistant agent that provides current conditions, forecasts, and weather"
)
# MCP tools are automatically available alongside regular function tools. 

@helloAgent.tool(name="hello_world")
async def hello_world():
    """
    Simple tool that responds with "Hello, World!".
    
    Args:
        req: HTTP request object
    
    Returns:
        HTTP response with "Hello, World!"
    """
    return "Hello, World!"

# Register the Hello World Agent (HTTP mode)
framework.register_agent(AgentConfig(
    name="hello_world_agent",
    call_mode=CallMode.HTTP,
    endpoint="http://localhost:7071/api", # Will call the same function app for demo purposes
    timeout=30
))

#########################################
# PART 2: MCP Server Definition
#########################################

from mcp.client import MCPClientHelper
from mcp.schema import ToolDefinition, ParameterDefinition

# Create MCP client helper for this app
mcp = MCPClientHelper(app)

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="hello_mcp",
    description="Say hello to a user through MCP",
    toolProperties=json.dumps([{
        "propertyName": "user_name",
        "propertyType": "string",
        "description": "The name of the user."
    }])
)
def hello_mcp(context) -> str:
    """MCP tool that greets a user by name"""
    content = json.loads(context)
    arguments = content.get("arguments", {})
    user_name = arguments.get("user_name", "Anonymous")
    return f"Hello {user_name}, I am MCPTool!"

@app.activity_trigger(input_name="req")
def mcp_call_service(req: Dict[str, Any]) -> str:
    """Activity to call MCP service"""
    tool_name = req.get("tool_name", "")
    arguments = req.get("arguments", {})
    
    if tool_name == "hello_mcp":
        user_name = arguments.get("user_name", "Anonymous")
        return f"Hello {user_name}, I am MCPTool!"
    else:
        return f"Unknown tool: {tool_name}"

# Register the MCP agent
framework.register_agent(AgentConfig(
    name="mcp_agent",
    call_mode=CallMode.MCP,
    timeout=30,
    extra_config={
        "client_type": "stdio",
        "server_command": ["python", "-m", "mcp.server"]  # Uses the mcp.server module as a fallback
    }
))

#########################################
# PART 3: Durable Orchestrator
#########################################

@orchestrator(framework)
def multi_agent_orchestrator(context: df.DurableOrchestrationContext, agents: AgentCaller):
    """
    Orchestrator function that calls both HTTP agent and MCP server
    
    Args:
        context: Durable orchestration context
        agents: Agent caller provided by the framework
        
    Returns:
        Object containing responses from both agents
    """
    # Get input parameters or use defaults
    input_data = context.get_input() or {}
    name = input_data.get("name", "Durable Orchestrator")
    
    # Call the Hello World agent over HTTP
    logging.info("Calling Hello World agent via HTTP...")
    hello_name_response = yield agents.call_http_agent(
        context,
        "hello_world_agent", 
        "hello_name", 
        {"name": name}
    )
    
    # Call the MCP tool using the agent framework
    logging.info("Calling MCP agent...")
    mcp_response = yield agents.call_mcp_tool(
        context,
        "mcp_agent",
        "hello_mcp",
        {"user_name": name}
    )
    
    # Return all responses
    return {
        "hello_name_response": hello_name_response,
        "mcp_response": mcp_response
    }

#########################################
# PART 4: HTTP Triggers
#########################################

@app.route(route="start_orchestration", auth_level=func.AuthLevel.ANONYMOUS)
@app.durable_client_input(client_name="client")
async def start_orchestration(req: func.HttpRequest, client: df.DurableOrchestrationClient):
    """HTTP trigger to start the orchestrator"""
    # Get name from query params, body, or use default
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}
    
    name = req.params.get("name", body.get("name", "Anonymous"))
    
    instance_id = await client.start_new(
        "multi_agent_orchestrator", 
        client_input={"name": name}
    )
    
    return client.create_check_status_response(req, instance_id)

@app.route(route="orchestrator_status/{instance_id}", auth_level=func.AuthLevel.ANONYMOUS)
@app.durable_client_input(client_name="client")
async def get_status(req: func.HttpRequest, client: df.DurableOrchestrationClient, instance_id: str):
    """HTTP trigger to check orchestrator status"""
    status = await client.get_status(instance_id)
    
    return func.HttpResponse(
        body=json.dumps(status),
        mimetype="application/json"
    )
