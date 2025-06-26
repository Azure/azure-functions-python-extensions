# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Anthropic provider implementation."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from ..types import ChatMessage, LLMConfig
from .base import BaseLLMProvider


def _check_anthropic_installed():
    """Check if anthropic package is installed and provide helpful error message."""
    try:
        import anthropic

        return anthropic
    except ImportError as e:
        raise ImportError(
            "Please install the `anthropic` package to use the Anthropic provider, "
            'you can use the `anthropic` optional group — `pip install "azurefunctions-agents-framework[anthropic]"`'
        ) from e


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic provider for chat completions.

    Supports Anthropic's Claude models with function calling capabilities.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the Anthropic provider."""
        super().__init__(config)
        self.logger = logging.getLogger("AnthropicProvider")

        # Check if anthropic is installed
        anthropic = _check_anthropic_installed()

        # Get API key
        api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "Anthropic API key not provided in config or ANTHROPIC_API_KEY environment variable. "
                "Set the `ANTHROPIC_API_KEY` environment variable or pass it via config."
            )

        # Initialize Anthropic client
        client_kwargs = {
            "api_key": api_key,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
        }

        if config.api_base:
            client_kwargs["base_url"] = config.api_base

        if config.extra_headers:
            client_kwargs["default_headers"] = config.extra_headers

        self.client = anthropic.AsyncAnthropic(**client_kwargs)

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a chat completion using Anthropic's API."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg.role == "system":
                    # Anthropic handles system messages separately
                    system_message = msg.content
                elif msg.role in ["user", "assistant"]:
                    anthropic_msg = {"role": msg.role, "content": msg.content}

                    # Handle tool calls for assistant messages
                    if msg.tool_calls:
                        anthropic_msg["content"] = []
                        if msg.content:
                            anthropic_msg["content"].append(
                                {"type": "text", "text": msg.content}
                            )

                        for tool_call in msg.tool_calls:
                            anthropic_msg["content"].append(
                                {
                                    "type": "tool_use",
                                    "id": tool_call["id"],
                                    "name": tool_call["function"]["name"],
                                    "input": (
                                        tool_call["function"]["arguments"]
                                        if isinstance(
                                            tool_call["function"]["arguments"], dict
                                        )
                                        else {}
                                    ),
                                }
                            )

                    anthropic_messages.append(anthropic_msg)
                elif msg.role == "tool":
                    # Handle tool response messages
                    anthropic_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": msg.tool_call_id,
                                    "content": msg.content,
                                }
                            ],
                        }
                    )

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "messages": anthropic_messages,
                "temperature": self.config.temperature,
                **kwargs,
            }

            if system_message:
                request_params["system"] = system_message

            if self.config.max_tokens:
                request_params["max_tokens"] = self.config.max_tokens
            else:
                # Anthropic requires max_tokens parameter
                request_params["max_tokens"] = 4096

            # Handle tools
            if tools:
                anthropic_tools = []
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool.get("function", {})
                        anthropic_tools.append(
                            {
                                "name": func.get("name"),
                                "description": func.get("description", ""),
                                "input_schema": func.get("parameters", {}),
                            }
                        )

                if anthropic_tools:
                    request_params["tools"] = anthropic_tools

            # Make the API call
            response = await self.client.messages.create(**request_params)

            # Convert response to our standard format
            assistant_message = {"role": "assistant", "content": ""}

            tool_calls = []
            text_content = []

            for content_block in response.content:
                if content_block.type == "text":
                    text_content.append(content_block.text)
                elif content_block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": content_block.id,
                            "type": "function",
                            "function": {
                                "name": content_block.name,
                                "arguments": content_block.input,
                            },
                        }
                    )

            assistant_message["content"] = " ".join(text_content)
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls

            # Create a mock message object with required attributes
            class MockMessage:
                def __init__(self, role, content, tool_calls=None):
                    self.role = role
                    self.content = content
                    self.tool_calls = tool_calls or []

            return {
                "message": MockMessage(
                    role="assistant",
                    content=assistant_message["content"],
                    tool_calls=tool_calls,
                ),
                "usage": (
                    {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens
                        + response.usage.output_tokens,
                    }
                    if response.usage
                    else None
                ),
                "finish_reason": response.stop_reason,
                "id": response.id,
                "created": None,  # Anthropic doesn't provide timestamp
                "model": response.model,
            }

        except Exception as e:
            self.logger.error(f"Anthropic chat completion failed: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """Generate a streaming chat completion using Anthropic's API."""
        try:
            # Convert messages to Anthropic format (same as chat_completion)
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                elif msg.role in ["user", "assistant"]:
                    anthropic_msg = {"role": msg.role, "content": msg.content}

                    if msg.tool_calls:
                        anthropic_msg["content"] = []
                        if msg.content:
                            anthropic_msg["content"].append(
                                {"type": "text", "text": msg.content}
                            )

                        for tool_call in msg.tool_calls:
                            anthropic_msg["content"].append(
                                {
                                    "type": "tool_use",
                                    "id": tool_call["id"],
                                    "name": tool_call["function"]["name"],
                                    "input": (
                                        tool_call["function"]["arguments"]
                                        if isinstance(
                                            tool_call["function"]["arguments"], dict
                                        )
                                        else {}
                                    ),
                                }
                            )

                    anthropic_messages.append(anthropic_msg)
                elif msg.role == "tool":
                    anthropic_messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": msg.tool_call_id,
                                    "content": msg.content,
                                }
                            ],
                        }
                    )

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "messages": anthropic_messages,
                "temperature": self.config.temperature,
                "stream": True,
                **kwargs,
            }

            if system_message:
                request_params["system"] = system_message

            if self.config.max_tokens:
                request_params["max_tokens"] = self.config.max_tokens
            else:
                request_params["max_tokens"] = 4096

            # Handle tools
            if tools:
                anthropic_tools = []
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool.get("function", {})
                        anthropic_tools.append(
                            {
                                "name": func.get("name"),
                                "description": func.get("description", ""),
                                "input_schema": func.get("parameters", {}),
                            }
                        )

                if anthropic_tools:
                    request_params["tools"] = anthropic_tools

            # Make the streaming API call
            stream = await self.client.messages.create(**request_params)

            async for chunk in stream:
                if (
                    chunk.type == "content_block_delta"
                    and chunk.delta.type == "text_delta"
                ):
                    yield {
                        "delta": {"content": chunk.delta.text},
                        "finish_reason": None,
                        "id": None,
                        "created": None,
                        "model": None,
                    }
                elif chunk.type == "message_stop":
                    yield {
                        "delta": {},
                        "finish_reason": (
                            chunk.stop_reason
                            if hasattr(chunk, "stop_reason")
                            else "stop"
                        ),
                        "id": None,
                        "created": None,
                        "model": None,
                    }

        except Exception as e:
            self.logger.error(f"Anthropic streaming completion failed: {e}")
            raise
