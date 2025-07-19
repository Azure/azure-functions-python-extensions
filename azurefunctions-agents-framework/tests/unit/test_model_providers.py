"""Unit tests for Azure Functions Agent Framework model providers.

This module tests the LLM provider implementations including OpenAI, Azure OpenAI,
Anthropic, Google, and other provider integrations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from azurefunctions.agents.model_providers.azure_openai_provider import (
    AzureOpenAIProvider,
)
from azurefunctions.agents.model_providers.base import BaseLLMProvider
from azurefunctions.agents.model_providers.client import LLMClient
from azurefunctions.agents.model_providers.openai_provider import OpenAIProvider
from azurefunctions.agents.types import ChatMessage, LLMConfig, LLMProvider


class TestBaseLLMProvider:
    """Test the base LLM provider abstract class."""

    def test_base_provider_cannot_be_instantiated(self):
        """Test that BaseLLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider(Mock())

    def test_base_provider_abstract_methods(self):
        """Test that BaseLLMProvider defines abstract methods."""
        # Check that the abstract methods exist
        assert hasattr(BaseLLMProvider, "chat_completion")
        assert hasattr(BaseLLMProvider, "stream_completion")


class TestLLMClient:
    """Test the LLM client that manages provider instances."""

    def test_llm_client_openai_provider_creation(self):
        """Test LLMClient creates OpenAI provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        with patch(
            "azurefunctions.agents.model_providers.client._import_openai_provider"
        ) as mock_import:
            mock_provider_class = Mock()
            mock_import.return_value = mock_provider_class

            LLMClient(config)
            mock_provider_class.assert_called_once_with(config)

    def test_llm_client_azure_openai_provider_creation(self):
        """Test LLMClient creates Azure OpenAI provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
        )

        with patch(
            "azurefunctions.agents.model_providers.client._import_azure_openai_provider"
        ) as mock_import:
            mock_provider_class = Mock()
            mock_import.return_value = mock_provider_class

            LLMClient(config)
            mock_provider_class.assert_called_once_with(config)

    def test_llm_client_anthropic_provider_creation(self):
        """Test LLMClient creates Anthropic provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            api_key="test-key",
        )

        with patch(
            "azurefunctions.agents.model_providers.client._import_anthropic_provider"
        ) as mock_import:
            mock_provider_class = Mock()
            mock_import.return_value = mock_provider_class

            LLMClient(config)
            mock_provider_class.assert_called_once_with(config)

    def test_llm_client_google_provider_creation(self):
        """Test LLMClient creates Google provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.GOOGLE, model_name="gemini-pro", api_key="test-key"
        )

        with patch(
            "azurefunctions.agents.model_providers.client._import_google_provider"
        ) as mock_import:
            mock_provider_class = Mock()
            mock_import.return_value = mock_provider_class

            LLMClient(config)
            mock_provider_class.assert_called_once_with(config)

    def test_llm_client_unsupported_provider(self):
        """Test LLMClient handles unsupported provider."""
        config = LLMConfig(
            provider="unsupported_provider", model_name="test-model"  # Invalid provider
        )

        with pytest.raises((ValueError, AttributeError)):
            LLMClient(config)

    @pytest.mark.asyncio
    async def test_llm_client_chat_completion_delegation(self):
        """Test that LLMClient delegates chat_completion to provider."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        mock_provider = Mock()
        mock_provider.chat_completion = AsyncMock(return_value={"message": {"content": "Test response"}})

        with patch(
            "azurefunctions.agents.model_providers.client._import_openai_provider",
            return_value=Mock(return_value=mock_provider)
        ):
            client = LLMClient(config)
            messages = [ChatMessage(role="user", content="Test prompt")]
            response = await client.chat_completion(messages)

            mock_provider.chat_completion.assert_called_once_with(messages=messages, tools=None, tool_choice=None)
            assert response["message"]["content"] == "Test response"

    @pytest.mark.asyncio
    async def test_llm_client_stream_completion_delegation(self):
        """Test that LLMClient delegates stream_completion to provider."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        async def mock_stream(*args, **kwargs):
            yield {"delta": {"content": "Test"}}
            yield {"delta": {"content": " response"}}

        mock_provider = Mock()
        mock_provider.stream_completion = mock_stream

        with patch(
            "azurefunctions.agents.model_providers.client._import_openai_provider",
            return_value=Mock(return_value=mock_provider)
        ):
            client = LLMClient(config)
            messages = [ChatMessage(role="user", content="Test prompt")]

            # Consume the stream to verify it works
            chunks = []
            async for chunk in client.stream_completion(messages):
                chunks.append(chunk)
            assert len(chunks) == 2


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key",
            api_base="https://api.openai.com",
            temperature=0.8,
            max_tokens=1500,
        )

        with patch(
            "azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI"
        ) as mock_openai:
            OpenAIProvider(config)

            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["api_key"] == "test-key"
            assert call_kwargs["base_url"] == "https://api.openai.com"

    def test_openai_provider_missing_api_key(self):
        """Test OpenAI provider with missing API key."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            # No api_key provided
        )

        with patch("azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI"):
            with pytest.raises((ValueError, ImportError)):
                OpenAIProvider(config)

    def test_openai_provider_config_validation(self):
        """Test OpenAI provider validates configuration."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        with patch("azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI"):
            provider = OpenAIProvider(config)
            assert provider.config == config

    @patch("azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_openai_provider_chat_completion(self, mock_openai_class):
        """Test OpenAI provider chat_completion method."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Create a proper mock message object
        mock_message = Mock()
        mock_message.content = "Test response from OpenAI"
        mock_message.tool_calls = None

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = mock_message
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = None
        mock_response.id = "test-id"
        mock_response.created = 123456789
        mock_response.model = "gpt-4"

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIProvider(config)
        messages = [ChatMessage(role="user", content="Test prompt")]
        response = await provider.chat_completion(messages)

        # Verify the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.7  # Default from config
        assert len(call_kwargs["messages"]) > 0

        assert response["message"].content == "Test response from OpenAI"
        assert response["finish_reason"] == "stop"


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider implementation."""

    def test_azure_openai_provider_initialization(self):
        """Test Azure OpenAI provider initialization."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
            api_version="2023-12-01-preview",
        )

        with patch(
            "azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI"
        ) as mock_azure_openai:
            AzureOpenAIProvider(config)

            mock_azure_openai.assert_called_once()
            call_kwargs = mock_azure_openai.call_args[1]
            assert call_kwargs["api_key"] == "test-key"
            assert call_kwargs["azure_endpoint"] == "https://test.openai.azure.com"
            assert call_kwargs["api_version"] == "2023-12-01-preview"

    def test_azure_openai_provider_missing_endpoint(self):
        """Test Azure OpenAI provider with missing endpoint."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            api_key="test-key",
            # Missing azure_endpoint
        )

        with patch(
            "azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI"
        ):
            with pytest.raises((ValueError, ImportError)):
                AzureOpenAIProvider(config)

    def test_azure_openai_provider_missing_deployment(self):
        """Test Azure OpenAI provider with missing deployment uses model name."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            api_key="test-key",
            # Missing azure_deployment - should use model_name
        )

        with patch(
            "azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI"
        ):
            provider = AzureOpenAIProvider(config)
            # Should use model_name as deployment when azure_deployment is not provided
            assert provider.deployment_name == "gpt-4"

    @patch("azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI")
    async def test_azure_openai_provider_chat_completion(self, mock_azure_openai_class):
        """Test Azure OpenAI provider chat_completion method."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
        )

        # Mock the Azure OpenAI client and response
        mock_client = AsyncMock()
        mock_azure_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response from Azure OpenAI"
        mock_client.chat.completions.create.return_value = mock_response

        provider = AzureOpenAIProvider(config)
        messages = [ChatMessage(role="user", content="Test prompt")]
        response = await provider.chat_completion(messages)

        # Verify the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4-deployment"  # Should use deployment name

        # Check that response is a dict containing the message
        assert isinstance(response, dict)
        assert response["message"].content == "Test response from Azure OpenAI"


class TestProviderErrorHandling:
    """Test error handling across providers."""

    @patch("azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI")
    async def test_openai_provider_api_error_handling(self, mock_openai_class):
        """Test OpenAI provider handles API errors."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Simulate API error
        from openai import APIError
        import httpx

        mock_request = Mock()
        mock_client.chat.completions.create.side_effect = APIError(
            "API Error", request=mock_request, body="Error details"
        )

        provider = OpenAIProvider(config)

        with pytest.raises(APIError):
            await provider.chat_completion([ChatMessage(role="user", content="Test prompt")])

    @patch("azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI")
    async def test_openai_provider_rate_limit_handling(self, mock_openai_class):
        """Test OpenAI provider handles rate limit errors."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-4", api_key="test-key"
        )

        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Simulate rate limit error
        from openai import RateLimitError
        import httpx

        mock_response = Mock()
        mock_response.request = Mock()
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Rate limit exceeded", response=mock_response, body="Rate limit details"
        )

        provider = OpenAIProvider(config)

        with pytest.raises(RateLimitError):
            await provider.chat_completion([ChatMessage(role="user", content="Test prompt")])

    def test_provider_import_error_handling(self):
        """Test provider handles missing dependency imports."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            api_key="test-key",
        )

        # Test when anthropic package is not installed
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError):
                from azurefunctions.agents.model_providers.anthropic_provider import (
                    AnthropicProvider,
                )

                AnthropicProvider(config)


class TestProviderConfiguration:
    """Test provider configuration and parameter handling."""

    def test_openai_provider_custom_parameters(self):
        """Test OpenAI provider with custom parameters."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key",
            temperature=0.9,
            max_tokens=2000,
            timeout=60,
            max_retries=5,
            extra_headers={"X-Custom": "header"},
            extra_body={"custom_param": "value"},
        )

        with patch(
            "azurefunctions.agents.model_providers.openai_provider.AsyncOpenAI"
        ) as mock_openai:
            OpenAIProvider(config)

            # Verify configuration parameters are passed
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["timeout"] == 60
            assert call_kwargs["max_retries"] == 5
            assert call_kwargs["default_headers"] == {"X-Custom": "header"}

    def test_azure_openai_provider_api_version_handling(self):
        """Test Azure OpenAI provider API version handling."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
            api_version="2024-02-01",
        )

        with patch(
            "azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI"
        ) as mock_azure_openai:
            AzureOpenAIProvider(config)

            call_kwargs = mock_azure_openai.call_args[1]
            assert call_kwargs["api_version"] == "2024-02-01"

    async def test_provider_model_name_mapping(self):
        """Test that providers correctly map model names."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
        )

        with patch(
            "azurefunctions.agents.model_providers.azure_openai_provider.AsyncAzureOpenAI"
        ) as mock_azure_openai:
            mock_client = AsyncMock()
            mock_azure_openai.return_value = mock_client

            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response

            provider = AzureOpenAIProvider(config)
            await provider.chat_completion([ChatMessage(role="user", content="Test")])

            # For Azure OpenAI, model should be the deployment name
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4-deployment"
