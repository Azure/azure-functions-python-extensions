# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""LLM Client - unified interface for different model providers."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..types import ChatMessage, LLMConfig, LLMProvider


def _import_openai_provider():
    """Lazy import for OpenAI provider to handle optional dependency."""
    try:
        from .openai_provider import OpenAIProvider

        return OpenAIProvider
    except ImportError:
        return None


def _import_azure_openai_provider():
    """Lazy import for Azure OpenAI provider to handle optional dependency."""
    try:
        from .azure_openai_provider import AzureOpenAIProvider

        return AzureOpenAIProvider
    except ImportError:
        return None


def _import_anthropic_provider():
    """Lazy import for Anthropic provider to handle optional dependency."""
    try:
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider
    except ImportError:
        return None


def _import_google_provider():
    """Lazy import for Google provider to handle optional dependency."""
    try:
        from .google_provider import GoogleProvider

        return GoogleProvider
    except ImportError:
        return None


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
            OpenAIProvider = _import_openai_provider()
            if OpenAIProvider is None:
                raise ImportError(
                    "Please install the `openai` package to use the OpenAI provider, "
                    'you can use the `openai` optional group — `pip install "azurefunctions-agents-framework[openai]"`'
                )
            return OpenAIProvider(self.config)
        elif self.config.provider == LLMProvider.AZURE_OPENAI:
            AzureOpenAIProvider = _import_azure_openai_provider()
            if AzureOpenAIProvider is None:
                raise ImportError(
                    "Please install the `openai` package to use the Azure OpenAI provider, "
                    'you can use the `openai` optional group — `pip install "azurefunctions-agents-framework[openai]"`'
                )
            return AzureOpenAIProvider(self.config)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            AnthropicProvider = _import_anthropic_provider()
            if AnthropicProvider is None:
                raise ImportError(
                    "Please install the `anthropic` package to use the Anthropic provider, "
                    'you can use the `anthropic` optional group — `pip install "azurefunctions-agents-framework[anthropic]"`'
                )
            return AnthropicProvider(self.config)
        elif self.config.provider == LLMProvider.GOOGLE:
            GoogleProvider = _import_google_provider()
            if GoogleProvider is None:
                raise ImportError(
                    "Please install the `google-genai` package to use the Google provider, "
                    'you can use the `google` optional group — `pip install "azurefunctions-agents-framework[google]"`'
                )
            return GoogleProvider(self.config)
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
