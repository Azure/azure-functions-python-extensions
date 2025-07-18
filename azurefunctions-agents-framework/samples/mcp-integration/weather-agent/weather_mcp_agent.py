#!/usr/bin/env python3
"""
Weather Agent with MCP Integration Example

This example demonstrates how to integrate a Model Context Protocol (MCP) server
with an Azure Functions agent. The agent can use MCP tools to fetch weather data
and answer weather-related questions.

To run this example:
1. Install the weather MCP server: https://github.com/modelcontextprotocol/servers/tree/main/src/weather
2. Set your OpenAI API key in environment variables
3. Deploy to Azure Functions or run locally

For local testing:
    func start

Example request:
    POST /api/weather_agent
    {
        "messages": [
            {"role": "user", "content": "What's the weather like in San Francisco?"}
        ]
    }
"""

import asyncio
import json
import logging
import os
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


async def handle_weather_request(
    messages: List[ChatMessage], llm_config: LLMConfig
) -> ChatMessage:
    """Handle weather request using MCP integration."""

    # Create MCP server for weather tools
    # This example assumes you have the weather MCP server installed
    # GitHub: https://github.com/modelcontextprotocol/servers/tree/main/src/weather
    weather_mcp = MCPServer(
        name="weather-tools",
        mode=MCPServerMode.STDIO,
        params=MCPServerStdioParams(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-weather"],
            env={"WEATHER_API_KEY": os.getenv("WEATHER_API_KEY", "demo")},
        ),
        cache_tools_list=True,  # Cache tools for better performance
    )

    # Create agent with MCP integration
    agent = Agent(
        name="WeatherAgent",
        instructions="""You are a helpful weather assistant. Use the available weather tools
        to provide accurate weather information when users ask about weather conditions,
        forecasts, or climate data. Always include relevant details like temperature,
        conditions, and any important weather alerts.""",
        llm_config=llm_config,
        mcp_servers=[weather_mcp],
    )

    # Get response from agent
    response = await agent.run(messages=messages)
    return response


# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7,
)

# Create the weather agent
weather_agent = Agent(
    name="WeatherAgent",
    instructions="""You are a helpful weather assistant. Use the available weather tools
    to provide accurate weather information when users ask about weather conditions,
    forecasts, or climate data. Always include relevant details like temperature,
    conditions, and any important weather alerts.""",
    llm_config=llm_config,
    mcp_servers=[
        MCPServer(
            name="weather-tools",
            mode=MCPServerMode.STDIO,
            params=MCPServerStdioParams(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-weather"],
                env={"WEATHER_API_KEY": os.getenv("WEATHER_API_KEY", "demo")},
            ),
            cache_tools_list=True,
        )
    ],
)

# Create Function App with the weather agent
app = AgentFunctionApp(agents={"WeatherAgent": weather_agent})


@app.route(route="weather_agent", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def weather_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for weather agent."""

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

        messages = [ChatMessage(**msg) for msg in req_body["messages"]]

        # Get response from the weather agent
        response = await weather_agent.run(messages=messages)

        return func.HttpResponse(
            json.dumps({"response": response.content, "role": response.role}),
            status_code=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error in weather agent: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""

    return func.HttpResponse(
        json.dumps(
            {
                "status": "healthy",
                "agent": "WeatherAgent",
                "mcp_integration": "enabled",
                "weather_server": "available",
            }
        ),
        status_code=200,
        mimetype="application/json",
    )


if __name__ == "__main__":
    # For local testing
    import asyncio

    async def test_agent():
        """Test the agent locally."""
        messages = [
            ChatMessage(
                role="user", content="What's the weather like in New York City?"
            )
        ]

        # Note: This requires the weather MCP server to be available
        try:
            response = await handle_weather_request(messages, llm_config)
            print(f"Agent response: {response.content}")

        except Exception as e:
            print(f"Test failed: {e}")
            print("Note: This example requires the weather MCP server to be installed.")
            print("Run: npm install -g @modelcontextprotocol/server-weather")

    asyncio.run(test_agent())
