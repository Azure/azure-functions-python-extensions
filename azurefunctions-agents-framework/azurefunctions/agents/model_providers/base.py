# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Base provider interface for LLM providers."""

import abc
from typing import Any, Dict, List, Optional

from ..types import ChatMessage, LLMConfig


class BaseLLMProvider(abc.ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers should inherit from this class and implement the required methods.
    """

    def __init__(self, config: LLMConfig):
        """Initialize the provider with configuration."""
        self.config = config

    @abc.abstractmethod
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion.

        Args:
            messages: List of chat messages
            tools: Optional list of tool schemas for function calling
            tool_choice: Optional tool choice strategy
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing the response message and metadata
        """
        pass

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """
        Generate a streaming chat completion (optional).

        Args:
            messages: List of chat messages
            tools: Optional list of tool schemas for function calling
            tool_choice: Optional tool choice strategy
            **kwargs: Additional provider-specific parameters

        Yields:
            Response chunks as they become available
        """
        # Default implementation - fallback to non-streaming
        response = await self.chat_completion(
            messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
        )
        yield response

    async def initialize(self):
        """Initialize the provider (optional)."""
        pass
