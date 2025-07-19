# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Streaming response support for Azure Functions Agent framework."""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

try:
    from azurefunctions.extensions.http.fastapi import StreamingResponse

    FASTAPI_STREAMING_AVAILABLE = True
except ImportError:
    FASTAPI_STREAMING_AVAILABLE = False

    # Fallback for when FastAPI streaming is not available
    class StreamingResponse:
        def __init__(self, content, media_type="text/plain"):
            self.content = content
            self.media_type = media_type


class AgentStreamingResponse:
    """
    Handles streaming responses from agents using Server-Sent Events (SSE).

    This class provides a bridge between the agent's streaming capabilities
    and Azure Functions streaming responses.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def create_streaming_response(
        self,
        agent_stream: AsyncGenerator[Dict[str, Any], None],
        event_type: str = "message",
    ) -> StreamingResponse:
        """
        Create a StreamingResponse from an agent's async generator.

        Args:
            agent_stream: Async generator yielding agent response chunks
            event_type: SSE event type (default: "message")

        Returns:
            StreamingResponse configured for SSE
        """
        if not FASTAPI_STREAMING_AVAILABLE:
            raise ImportError(
                "FastAPI streaming extension not available. "
                "Install with: pip install azurefunctions-extensions-http-fastapi"
            )

        async def generate_sse() -> AsyncGenerator[str, None]:
            """Generate Server-Sent Events format."""
            try:
                # Send initial connection event
                yield f"event: connect\ndata: {json.dumps({'status': 'connected'})}\n\n"

                # Stream agent responses
                async for chunk in agent_stream:
                    # Format as SSE
                    data = json.dumps(chunk)
                    yield f"event: {event_type}\ndata: {data}\n\n"

                # Send completion event
                yield f"event: complete\ndata: {json.dumps({'status': 'completed'})}\n\n"

            except Exception as e:
                self.logger.error(f"Error in streaming response: {e}")
                # Send error event
                error_data = json.dumps(
                    {"status": "error", "error": str(e), "error_type": type(e).__name__}
                )
                yield f"event: error\ndata: {error_data}\n\n"

        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    async def create_simple_stream(
        self, content_generator: AsyncGenerator[str, None]
    ) -> StreamingResponse:
        """
        Create a simple streaming response for plain text content.

        Args:
            content_generator: Async generator yielding text chunks

        Returns:
            StreamingResponse for plain text streaming
        """
        if not FASTAPI_STREAMING_AVAILABLE:
            raise ImportError(
                "FastAPI streaming extension not available. "
                "Install with: pip install azurefunctions-extensions-http-fastapi"
            )

        return StreamingResponse(
            content_generator,
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )


async def create_agent_stream(
    agent, request_data: Dict[str, Any], logger: Optional[logging.Logger] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Create a streaming response from an agent.

    Args:
        agent: The agent instance to stream from
        request_data: Request data to process
        logger: Optional logger instance

    Yields:
        Dict[str, Any]: Streaming response chunks
    """
    logger = logger or logging.getLogger(__name__)

    try:
        # Check if agent supports streaming
        if not hasattr(agent, "llm_client") or not agent.llm_client:
            # Fallback: return single response
            response = await agent.process_request(request_data)
            yield {
                "type": "response",
                "content": response.get("response", ""),
                "metadata": {
                    "agent": agent.name,
                    "streaming": False,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            }
            return

        # Check if LLM client supports streaming
        if not hasattr(agent.llm_client, "stream_completion"):
            # Fallback: return single response
            response = await agent.process_request(request_data)
            yield {
                "type": "response",
                "content": response.get("response", ""),
                "metadata": {
                    "agent": agent.name,
                    "streaming": False,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            }
            return

        # Prepare messages for streaming
        messages = request_data.get("messages", [])
        message = request_data.get("message", "")
        request_data.get("context", {})

        # Convert simple message to messages format
        if message and not messages:
            messages = [{"role": "user", "content": message}]

        if not messages:
            yield {
                "type": "error",
                "content": "No messages provided for streaming",
                "metadata": {"agent": agent.name},
            }
            return

        # Convert to ChatMessage objects
        from .types import ChatMessage

        chat_messages = []
        for msg in messages:
            chat_messages.append(
                ChatMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id"),
                    name=msg.get("name"),
                )
            )

        # Add system message if agent has instructions
        if agent.instructions:
            instructions = await agent._get_instructions()
            system_message = ChatMessage(role="system", content=instructions)
            chat_messages.insert(0, system_message)

        # Get tools if available
        tools = None
        if hasattr(agent, "tool_registry") and agent.tool_registry:
            tools = agent.tool_registry.get_tools_schema()

        # Start streaming
        collected_content = []

        yield {
            "type": "start",
            "content": "",
            "metadata": {
                "agent": agent.name,
                "streaming": True,
                "timestamp": asyncio.get_event_loop().time(),
            },
        }

        # Stream from LLM
        async for chunk in agent.llm_client.stream_completion(
            messages=chat_messages, tools=tools
        ):
            if chunk.get("delta") and chunk["delta"].get("content"):
                content = chunk["delta"]["content"]
                collected_content.append(content)

                yield {
                    "type": "delta",
                    "content": content,
                    "metadata": {
                        "agent": agent.name,
                        "chunk_id": chunk.get("id"),
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                }

            # Handle tool calls if present
            if chunk.get("delta") and chunk["delta"].get("tool_calls"):
                yield {
                    "type": "tool_call",
                    "content": chunk["delta"]["tool_calls"],
                    "metadata": {
                        "agent": agent.name,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                }

        # Send final response
        full_response = "".join(collected_content)
        yield {
            "type": "complete",
            "content": full_response,
            "metadata": {
                "agent": agent.name,
                "total_length": len(full_response),
                "timestamp": asyncio.get_event_loop().time(),
            },
        }

    except Exception as e:
        logger.error(f"Error in agent streaming: {e}")
        yield {
            "type": "error",
            "content": f"Streaming error: {str(e)}",
            "metadata": {
                "agent": agent.name if agent else "unknown",
                "error_type": type(e).__name__,
                "timestamp": asyncio.get_event_loop().time(),
            },
        }
