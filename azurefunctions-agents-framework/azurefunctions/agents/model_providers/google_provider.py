# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Google AI provider implementation."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from ..types import ChatMessage, LLMConfig
from .base import BaseLLMProvider


def _check_google_genai_installed():
    """Check if google-genai package is installed and provide helpful error message."""
    try:
        from google import genai
        from google.auth.credentials import Credentials

        return genai, Credentials
    except ImportError as e:
        raise ImportError(
            "Please install the `google-genai` package to use the Google provider, "
            'you can use the `google` optional group — `pip install "azurefunctions-agents-framework[google]"`'
        ) from e


class GoogleProvider(BaseLLMProvider):
    """
    Google AI provider for chat completions.

    Supports Google's Gemini models with function calling capabilities.
    Supports both Google AI Studio (with API key) and Vertex AI (with credentials).
    """

    def __init__(self, config: LLMConfig):
        """Initialize the Google provider."""
        super().__init__(config)
        self.logger = logging.getLogger("GoogleProvider")

        # Check if google-genai is installed
        genai, Credentials = _check_google_genai_installed()

        # Determine if we're using Vertex AI or Google AI Studio
        api_key = (
            config.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        )
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")

        # Use Vertex AI if project or location is specified, otherwise use Google AI Studio
        use_vertexai = bool(project or location or not api_key)

        if not use_vertexai:
            if not api_key:
                raise ValueError(
                    "Google API key not provided in config or GOOGLE_API_KEY environment variable. "
                    "Set the `GOOGLE_API_KEY` environment variable or pass it via config."
                )

            # Initialize Google AI Studio client
            self.client = genai.Client(
                vertexai=False,
                api_key=api_key,
                http_options={
                    "headers": {"User-Agent": "azurefunctions-agents-framework"}
                },
            )
        else:
            # Initialize Vertex AI client
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                http_options={
                    "headers": {"User-Agent": "azurefunctions-agents-framework"}
                },
            )

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a chat completion using Google's API."""
        try:
            # Convert messages to Google format
            google_messages = []
            system_instruction = None

            for msg in messages:
                if msg.role == "system":
                    # Google handles system messages as system_instruction
                    system_instruction = msg.content
                elif msg.role == "user":
                    google_messages.append(
                        {"role": "user", "parts": [{"text": msg.content}]}
                    )
                elif msg.role == "assistant":
                    parts = []
                    if msg.content:
                        parts.append({"text": msg.content})

                    # Handle tool calls
                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            parts.append(
                                {
                                    "function_call": {
                                        "name": tool_call["function"]["name"],
                                        "args": (
                                            tool_call["function"]["arguments"]
                                            if isinstance(
                                                tool_call["function"]["arguments"], dict
                                            )
                                            else {}
                                        ),
                                    }
                                }
                            )

                    google_messages.append(
                        {
                            "role": "model",  # Google uses "model" instead of "assistant"
                            "parts": parts,
                        }
                    )
                elif msg.role == "tool":
                    # Handle tool response messages
                    google_messages.append(
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "function_response": {
                                        "name": msg.name or "unknown_function",
                                        "response": {"result": msg.content},
                                    }
                                }
                            ],
                        }
                    )

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "contents": google_messages,
                **kwargs,
            }

            if system_instruction:
                request_params["system_instruction"] = system_instruction

            # Configure generation parameters
            generation_config = {
                "temperature": self.config.temperature,
            }
            if self.config.max_tokens:
                generation_config["max_output_tokens"] = self.config.max_tokens

            request_params["config"] = generation_config

            # Handle tools
            if tools:
                google_tools = []
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool.get("function", {})
                        google_tools.append(
                            {
                                "function_declarations": [
                                    {
                                        "name": func.get("name"),
                                        "description": func.get("description", ""),
                                        "parameters": func.get("parameters", {}),
                                    }
                                ]
                            }
                        )

                if google_tools:
                    request_params["tools"] = google_tools

            # Make the API call
            response = await self.client.agenerate_content(**request_params)

            # Convert response to our standard format
            assistant_message_content = ""
            tool_calls = []

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        assistant_message_content += part.text
                    elif hasattr(part, "function_call"):
                        tool_calls.append(
                            {
                                "id": f"call_{len(tool_calls)}",  # Google doesn't provide call IDs
                                "type": "function",
                                "function": {
                                    "name": part.function_call.name,
                                    "arguments": (
                                        dict(part.function_call.args)
                                        if hasattr(part.function_call, "args")
                                        else {}
                                    ),
                                },
                            }
                        )

            # Create a mock message object with required attributes
            class MockMessage:
                def __init__(self, role, content, tool_calls=None):
                    self.role = role
                    self.content = content
                    self.tool_calls = tool_calls or []

            return {
                "message": MockMessage(
                    role="assistant",
                    content=assistant_message_content,
                    tool_calls=tool_calls,
                ),
                "usage": (
                    {
                        "prompt_tokens": (
                            response.usage_metadata.prompt_token_count
                            if response.usage_metadata
                            else 0
                        ),
                        "completion_tokens": (
                            response.usage_metadata.candidates_token_count
                            if response.usage_metadata
                            else 0
                        ),
                        "total_tokens": (
                            response.usage_metadata.total_token_count
                            if response.usage_metadata
                            else 0
                        ),
                    }
                    if hasattr(response, "usage_metadata") and response.usage_metadata
                    else None
                ),
                "finish_reason": (
                    response.candidates[0].finish_reason
                    if response.candidates
                    else "unknown"
                ),
                "id": None,  # Google doesn't provide response IDs
                "created": None,  # Google doesn't provide timestamps
                "model": self.config.model_name,
            }

        except Exception as e:
            self.logger.error(f"Google chat completion failed: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """Generate a streaming chat completion using Google's API."""
        try:
            # Convert messages to Google format (same as chat_completion)
            google_messages = []
            system_instruction = None

            for msg in messages:
                if msg.role == "system":
                    system_instruction = msg.content
                elif msg.role == "user":
                    google_messages.append(
                        {"role": "user", "parts": [{"text": msg.content}]}
                    )
                elif msg.role == "assistant":
                    parts = []
                    if msg.content:
                        parts.append({"text": msg.content})

                    if msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            parts.append(
                                {
                                    "function_call": {
                                        "name": tool_call["function"]["name"],
                                        "args": (
                                            tool_call["function"]["arguments"]
                                            if isinstance(
                                                tool_call["function"]["arguments"], dict
                                            )
                                            else {}
                                        ),
                                    }
                                }
                            )

                    google_messages.append({"role": "model", "parts": parts})
                elif msg.role == "tool":
                    google_messages.append(
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "function_response": {
                                        "name": msg.name or "unknown_function",
                                        "response": {"result": msg.content},
                                    }
                                }
                            ],
                        }
                    )

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "contents": google_messages,
                **kwargs,
            }

            if system_instruction:
                request_params["system_instruction"] = system_instruction

            # Configure generation parameters
            generation_config = {
                "temperature": self.config.temperature,
            }
            if self.config.max_tokens:
                generation_config["max_output_tokens"] = self.config.max_tokens

            request_params["config"] = generation_config

            # Handle tools
            if tools:
                google_tools = []
                for tool in tools:
                    if tool.get("type") == "function":
                        func = tool.get("function", {})
                        google_tools.append(
                            {
                                "function_declarations": [
                                    {
                                        "name": func.get("name"),
                                        "description": func.get("description", ""),
                                        "parameters": func.get("parameters", {}),
                                    }
                                ]
                            }
                        )

                if google_tools:
                    request_params["tools"] = google_tools

            # Make the streaming API call
            stream = self.client.agenerate_content_stream(**request_params)

            async for chunk in stream:
                if chunk.candidates and chunk.candidates[0].content:
                    text_content = ""
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, "text") and part.text:
                            text_content += part.text

                    if text_content:
                        yield {
                            "delta": {"content": text_content},
                            "finish_reason": None,
                            "id": None,
                            "created": None,
                            "model": self.config.model_name,
                        }

                # Handle finish reason
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    yield {
                        "delta": {},
                        "finish_reason": chunk.candidates[0].finish_reason,
                        "id": None,
                        "created": None,
                        "model": self.config.model_name,
                    }

        except Exception as e:
            self.logger.error(f"Google streaming completion failed: {e}")
            raise
