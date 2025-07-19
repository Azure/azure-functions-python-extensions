# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Azure Functions Agent with Streaming Responses

This sample demonstrates how to implement streaming chat responses
using Azure Functions with the FastAPI extension.

Requirements:
- azure-functions
- azurefunctions-extensions-http-fastapi
- azurefunctions-agents-framework
"""

import azure.functions as func
import logging
import os

from azurefunctions.agents import (
    Agent,
    AgentFunctionApp,
    LLMConfig,
    LLMProvider,
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create the Azure Functions App with streaming support
app = AgentFunctionApp()

# Create a streaming-enabled agent
streaming_agent = Agent(
    name="streaming_weather_agent",
    instructions="""You are a helpful weather assistant that provides detailed weather information.
    When responding, provide comprehensive information about weather conditions, forecasts, and recommendations.
    Always be conversational and engaging in your responses.""",
    llm_config=LLMConfig(
        provider=LLMProvider.AZURE_OPENAI,
        model_name="gpt-4",  # Use a model that supports streaming
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version="2024-02-15-preview",
        temperature=0.7,
    ),
    enable_conversational_agent=True,
)

# Add the agent to the app
app.add_agent(streaming_agent)

# The streaming endpoints are automatically created:
# POST /api/agents/streaming_weather_agent/stream - Streaming chat
# POST /streaming_weather_agent/stream - Compatibility streaming endpoint

# Example usage:
"""
# Using curl to test streaming:
curl -X POST "http://localhost:7071/api/agents/streaming_weather_agent/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather like today in Seattle?"}' \
  --no-buffer

# Using JavaScript fetch:
async function streamChat(message) {
    const response = await fetch('/api/agents/streaming_weather_agent/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                console.log('Received:', data);

                if (data.type === 'delta') {
                    // Update UI with incremental content
                    appendToChat(data.content);
                } else if (data.type === 'complete') {
                    // Final response received
                    console.log('Complete response:', data.content);
                }
            }
        }
    }
}

# Python client example:
import aiohttp
import asyncio
import json

async def stream_chat(message):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:7071/api/agents/streaming_weather_agent/stream',
            json={'message': message}
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"Received: {data}")

                    if data['type'] == 'delta':
                        print(data['content'], end='', flush=True)
                    elif data['type'] == 'complete':
                        print(f"\nFinal response: {data['content']}")

# Run the client
# asyncio.run(stream_chat("What's the weather in New York?"))
"""

# For testing without the FastAPI extension, regular endpoints are still available:
# POST /api/agents/streaming_weather_agent/chat - Non-streaming chat
# GET /api/agents/streaming_weather_agent/info - Agent information
# GET /api/health - Health check (shows streaming availability)

if __name__ == "__main__":
    print("Streaming agent setup complete!")
    print(f"Agent: {streaming_agent.name}")
    print("Endpoints available:")
    print("  - POST /api/agents/streaming_weather_agent/chat (non-streaming)")
    print("  - POST /api/agents/streaming_weather_agent/stream (streaming, requires FastAPI extension)")
    print("  - GET /api/agents/streaming_weather_agent/info")
    print("  - GET /api/health")
    print("\nTo enable streaming, install: pip install azurefunctions-extensions-http-fastapi")
