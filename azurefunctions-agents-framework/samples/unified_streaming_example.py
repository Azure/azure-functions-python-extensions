"""
Azure Functions Agent Framework - Unified Streaming Example

This demonstrates how streaming now works through the same /chat endpoints
instead of requiring separate /stream endpoints.

Streaming is automatically activated when:
1. Accept: text/event-stream header is sent
2. "stream": true is included in request body
3. X-Stream: true header is sent

No separate endpoints needed!
"""

import azure.functions as func
from azurefunctions.agents import AgentFunctionApp

# Create function app with streaming enabled
app = AgentFunctionApp(enable_streaming=True)

@app.agent(name="helpful_assistant")
def helpful_assistant():
    """A helpful assistant that can stream responses."""
    return {
        "name": "helpful_assistant",
        "instructions": "You are a helpful AI assistant. Provide clear, helpful responses.",
        "llm_client": None,  # Configure with your LLM client
    }

# That's it! No additional streaming endpoints needed.
# The built-in /api/agents/helpful_assistant/chat endpoint automatically handles:

# NON-STREAMING requests (normal JSON response):
# POST /api/agents/helpful_assistant/chat
# Content-Type: application/json
# {"message": "Hello"}

# STREAMING requests (Server-Sent Events):
# POST /api/agents/helpful_assistant/chat
# Accept: text/event-stream
# Content-Type: application/json
# {"message": "Hello"}

# OR with stream parameter:
# POST /api/agents/helpful_assistant/chat
# Content-Type: application/json
# {"message": "Hello", "stream": true}

# OR with X-Stream header:
# POST /api/agents/helpful_assistant/chat
# X-Stream: true
# Content-Type: application/json
# {"message": "Hello"}

if __name__ == "__main__":
    print("🎉 Unified Streaming Example")
    print("=" * 50)
    print("✅ Single endpoint handles both streaming and non-streaming")
    print("✅ No separate /stream endpoints needed")
    print("✅ Clean, RESTful API design")
    print("")
    print("Available endpoints:")
    print("- POST /api/agents/helpful_assistant/chat (unified)")
    print("- GET /api/health (shows streaming status)")
    print("")
    print("Streaming activation methods:")
    print("1. Add 'Accept: text/event-stream' header")
    print("2. Add 'stream': true in request body")
    print("3. Add 'X-Stream: true' header")
