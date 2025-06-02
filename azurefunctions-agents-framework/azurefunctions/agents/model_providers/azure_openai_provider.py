# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure OpenAI provider implementation."""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncAzureOpenAI

from ..types import ChatMessage, LLMConfig
from .base import BaseLLMProvider


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI provider for chat completions.

    Supports Azure OpenAI Service with function calling capabilities.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the Azure OpenAI provider."""
        super().__init__(config)
        self.logger = logging.getLogger("AzureOpenAIProvider")

        # Get required Azure OpenAI parameters
        azure_endpoint = config.azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = config.api_key or os.getenv("AZURE_OPENAI_API_KEY")
        api_version = config.api_version or os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
        )

        if not azure_endpoint:
            raise ValueError(
                "Azure OpenAI endpoint not provided in config or AZURE_OPENAI_ENDPOINT environment variable"
            )

        if not api_key:
            raise ValueError(
                "Azure OpenAI API key not provided in config or AZURE_OPENAI_API_KEY environment variable"
            )

        # Initialize Azure OpenAI client
        client_kwargs = {
            "api_key": api_key,
            "api_version": api_version,
            "azure_endpoint": azure_endpoint,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
        }

        if config.extra_headers:
            client_kwargs["default_headers"] = config.extra_headers

        self.client = AsyncAzureOpenAI(**client_kwargs)

        # Use deployment name if provided, otherwise use model name
        self.deployment_name = config.azure_deployment or config.model_name

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a chat completion using Azure OpenAI's API."""
        try:
            # Convert ChatMessage objects to Azure OpenAI format
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
                "model": self.deployment_name,  # Use deployment name for Azure
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
            self.logger.error(f"Azure OpenAI chat completion failed: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """Generate a streaming chat completion using Azure OpenAI's API."""
        try:
            # Convert ChatMessage objects to Azure OpenAI format
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
                "model": self.deployment_name,  # Use deployment name for Azure
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
            self.logger.error(f"Azure OpenAI streaming completion failed: {e}")
            raise
