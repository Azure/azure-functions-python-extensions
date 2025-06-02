# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""OpenAI provider implementation."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from ..types import ChatMessage, LLMConfig
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider for chat completions.

    Supports OpenAI's chat completion API with function calling capabilities.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the OpenAI provider."""
        super().__init__(config)
        self.logger = logging.getLogger("OpenAIProvider")

        # Get API key from config or environment
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not provided in config or OPENAI_API_KEY environment variable"
            )

        # Initialize OpenAI client
        client_kwargs = {
            "api_key": api_key,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
        }

        if config.api_base:
            client_kwargs["base_url"] = config.api_base

        if config.organization:
            client_kwargs["organization"] = config.organization

        if config.extra_headers:
            client_kwargs["default_headers"] = config.extra_headers

        self.client = AsyncOpenAI(**client_kwargs)

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a chat completion using OpenAI's API."""
        try:
            # Convert ChatMessage objects to OpenAI format
            openai_messages = []
            for msg in messages:
                openai_msg = {"role": msg.role, "content": msg.content}

                if msg.tool_calls:
                    openai_msg["tool_calls"] = msg.tool_calls

                if msg.tool_call_id:
                    openai_msg["tool_call_id"] = msg.tool_call_id

                if msg.name:
                    openai_msg["name"] = msg.name

                openai_messages.append(openai_msg)

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "messages": openai_messages,
                "temperature": self.config.temperature,
                **kwargs,
            }

            if self.config.max_tokens:
                request_params["max_tokens"] = self.config.max_tokens

            if tools:
                request_params["tools"] = tools

            if tool_choice:
                request_params["tool_choice"] = tool_choice

            # Make the API call
            response = await self.client.chat.completions.create(**request_params)

            # Convert response to our standard format
            return {
                "message": response.choices[0].message,
                "usage": response.usage.__dict__ if response.usage else None,
                "finish_reason": response.choices[0].finish_reason,
                "id": response.id,
                "created": response.created,
                "model": response.model,
            }

        except Exception as e:
            self.logger.error(f"OpenAI chat completion failed: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """Generate a streaming chat completion using OpenAI's API."""
        try:
            # Convert ChatMessage objects to OpenAI format
            openai_messages = []
            for msg in messages:
                openai_msg = {"role": msg.role, "content": msg.content}

                if msg.tool_calls:
                    openai_msg["tool_calls"] = msg.tool_calls

                if msg.tool_call_id:
                    openai_msg["tool_call_id"] = msg.tool_call_id

                if msg.name:
                    openai_msg["name"] = msg.name

                openai_messages.append(openai_msg)

            # Prepare request parameters
            request_params = {
                "model": self.config.model_name,
                "messages": openai_messages,
                "temperature": self.config.temperature,
                "stream": True,
                **kwargs,
            }

            if self.config.max_tokens:
                request_params["max_tokens"] = self.config.max_tokens

            if tools:
                request_params["tools"] = tools

            if tool_choice:
                request_params["tool_choice"] = tool_choice

            # Make the streaming API call
            stream = await self.client.chat.completions.create(**request_params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    yield {
                        "delta": chunk.choices[0].delta,
                        "finish_reason": chunk.choices[0].finish_reason,
                        "id": chunk.id,
                        "created": chunk.created,
                        "model": chunk.model,
                    }

        except Exception as e:
            self.logger.error(f"OpenAI streaming completion failed: {e}")
            raise
