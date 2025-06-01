"""LLM Client - unified interface for different model providers."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..types import ChatMessage, LLMConfig, LLMProvider
from .azure_openai_provider import AzureOpenAIProvider
from .openai_provider import OpenAIProvider


class LLMClient:
    """
    Unified LLM client that supports multiple providers.

    Provides a consistent interface for chat completion across different LLM providers.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize the LLM client with the specified configuration.

        Args:
            config: LLM configuration specifying provider and settings
        """
        self.config = config
        self.logger = logging.getLogger(f"LLMClient.{config.provider.value}")
        self._provider = self._create_provider()

    def _create_provider(self):
        """Create the appropriate provider based on configuration."""
        if self.config.provider == LLMProvider.OPENAI:
            return OpenAIProvider(self.config)
        elif self.config.provider == LLMProvider.AZURE_OPENAI:
            return AzureOpenAIProvider(self.config)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            # TODO: Implement Anthropic provider
            raise NotImplementedError("Anthropic provider not yet implemented")
        elif self.config.provider == LLMProvider.OLLAMA:
            # TODO: Implement Ollama provider
            raise NotImplementedError("Ollama provider not yet implemented")
        elif self.config.provider == LLMProvider.AZURE_AI:
            # TODO: Implement Azure AI provider
            raise NotImplementedError("Azure AI provider not yet implemented")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    async def initialize(self):
        """Initialize the provider if needed."""
        if hasattr(self._provider, "initialize"):
            await self._provider.initialize()

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion using the configured provider.

        Args:
            messages: List of chat messages
            tools: Optional list of tool schemas for function calling
            tool_choice: Optional tool choice strategy ("auto", "none", or specific tool)
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing the response message and metadata
        """
        try:
            return await self._provider.chat_completion(
                messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
            )
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise

    async def stream_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ):
        """
        Generate a streaming chat completion.

        Args:
            messages: List of chat messages
            tools: Optional list of tool schemas for function calling
            tool_choice: Optional tool choice strategy
            **kwargs: Additional provider-specific parameters

        Yields:
            Response chunks as they become available
        """
        if hasattr(self._provider, "stream_completion"):
            async for chunk in self._provider.stream_completion(
                messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
            ):
                yield chunk
        else:
            # Fallback to non-streaming for providers that don't support it
            response = await self.chat_completion(
                messages=messages, tools=tools, tool_choice=tool_choice, **kwargs
            )
            yield response

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider."""
        return {
            "provider": self.config.provider.value,
            "model_name": self.config.model_name,
            "api_base": getattr(self.config, "api_base", None),
            "azure_endpoint": getattr(self.config, "azure_endpoint", None),
        }
