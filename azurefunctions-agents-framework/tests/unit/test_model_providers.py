"""Unit tests for Azure Functions Agent Framework model providers.

This module tests the LLM provider implementations including OpenAI, Azure OpenAI,
Anthropic, Google, and other provider integrations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from azurefunctions.agents.types import LLMConfig, LLMProvider
from azurefunctions.agents.model_providers.base import BaseLLMProvider
from azurefunctions.agents.model_providers.client import LLMClient
from azurefunctions.agents.model_providers.openai_provider import OpenAIProvider
from azurefunctions.agents.model_providers.azure_openai_provider import AzureOpenAIProvider


class TestBaseLLMProvider:
    """Test the base LLM provider abstract class."""

    def test_base_provider_cannot_be_instantiated(self):
        """Test that BaseLLMProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLLMProvider(Mock())

    def test_base_provider_abstract_methods(self):
        """Test that BaseLLMProvider defines abstract methods."""
        # Check that the abstract methods exist
        assert hasattr(BaseLLMProvider, 'generate_response')
        assert hasattr(BaseLLMProvider, 'generate_response_async')


class TestLLMClient:
    """Test the LLM client that manages provider instances."""

    def test_llm_client_openai_provider_creation(self):
        """Test LLMClient creates OpenAI provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.client.OpenAIProvider') as mock_provider:
            client = LLMClient(config)
            mock_provider.assert_called_once_with(config)

    def test_llm_client_azure_openai_provider_creation(self):
        """Test LLMClient creates Azure OpenAI provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.client.AzureOpenAIProvider') as mock_provider:
            client = LLMClient(config)
            mock_provider.assert_called_once_with(config)

    def test_llm_client_anthropic_provider_creation(self):
        """Test LLMClient creates Anthropic provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.client.AnthropicProvider') as mock_provider:
            client = LLMClient(config)
            mock_provider.assert_called_once_with(config)

    def test_llm_client_google_provider_creation(self):
        """Test LLMClient creates Google provider correctly."""
        config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-pro",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.client.GoogleProvider') as mock_provider:
            client = LLMClient(config)
            mock_provider.assert_called_once_with(config)

    def test_llm_client_unsupported_provider(self):
        """Test LLMClient handles unsupported provider."""
        config = LLMConfig(
            provider="unsupported_provider",  # Invalid provider
            model_name="test-model"
        )
        
        with pytest.raises((ValueError, AttributeError)):
            LLMClient(config)

    def test_llm_client_generate_response_delegation(self):
        """Test that LLMClient delegates generate_response to provider."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "Test response"
        
        with patch('azurefunctions.agents.model_providers.client.OpenAIProvider', return_value=mock_provider):
            client = LLMClient(config)
            response = client.generate_response("Test prompt")
            
            mock_provider.generate_response.assert_called_once_with("Test prompt")
            assert response == "Test response"

    @pytest.mark.asyncio
    async def test_llm_client_generate_response_async_delegation(self):
        """Test that LLMClient delegates generate_response_async to provider."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        mock_provider = Mock()
        mock_provider.generate_response_async = AsyncMock(return_value="Async test response")
        
        with patch('azurefunctions.agents.model_providers.client.OpenAIProvider', return_value=mock_provider):
            client = LLMClient(config)
            response = await client.generate_response_async("Test prompt")
            
            mock_provider.generate_response_async.assert_called_once_with("Test prompt")
            assert response == "Async test response"


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
            max_tokens=1500
        )
        
        with patch('azurefunctions.agents.model_providers.openai_provider.OpenAI') as mock_openai:
            provider = OpenAIProvider(config)
            
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['api_key'] == "test-key"
            assert call_kwargs['base_url'] == "https://api.openai.com"

    def test_openai_provider_missing_api_key(self):
        """Test OpenAI provider with missing API key."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4"
            # No api_key provided
        )
        
        with patch('azurefunctions.agents.model_providers.openai_provider.OpenAI'):
            with pytest.raises((ValueError, ImportError)):
                OpenAIProvider(config)

    def test_openai_provider_config_validation(self):
        """Test OpenAI provider validates configuration."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.openai_provider.OpenAI'):
            provider = OpenAIProvider(config)
            assert provider.config == config

    @patch('azurefunctions.agents.model_providers.openai_provider.OpenAI')
    def test_openai_provider_generate_response(self, mock_openai_class):
        """Test OpenAI provider generate_response method."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        # Mock the OpenAI client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response from OpenAI"
        mock_client.chat.completions.create.return_value = mock_response
        
        provider = OpenAIProvider(config)
        response = provider.generate_response("Test prompt")
        
        # Verify the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == "gpt-4"
        assert call_kwargs['temperature'] == 0.7  # Default from config
        assert len(call_kwargs['messages']) > 0
        
        assert response == "Test response from OpenAI"

    @patch('azurefunctions.agents.model_providers.openai_provider.OpenAI')
    @pytest.mark.asyncio
    async def test_openai_provider_generate_response_async(self, mock_openai_class):
        """Test OpenAI provider generate_response_async method."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        # Mock the OpenAI async client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Async test response from OpenAI"
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(config)
        response = await provider.generate_response_async("Test prompt")
        
        # Verify the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == "gpt-4"
        
        assert response == "Async test response from OpenAI"


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
            api_version="2023-12-01-preview"
        )
        
        with patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI') as mock_azure_openai:
            provider = AzureOpenAIProvider(config)
            
            mock_azure_openai.assert_called_once()
            call_kwargs = mock_azure_openai.call_args[1]
            assert call_kwargs['api_key'] == "test-key"
            assert call_kwargs['azure_endpoint'] == "https://test.openai.azure.com"
            assert call_kwargs['api_version'] == "2023-12-01-preview"

    def test_azure_openai_provider_missing_endpoint(self):
        """Test Azure OpenAI provider with missing endpoint."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            api_key="test-key"
            # Missing azure_endpoint
        )
        
        with patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI'):
            with pytest.raises((ValueError, ImportError)):
                AzureOpenAIProvider(config)

    def test_azure_openai_provider_missing_deployment(self):
        """Test Azure OpenAI provider with missing deployment."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            api_key="test-key"
            # Missing azure_deployment
        )
        
        with patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI'):
            with pytest.raises((ValueError, ImportError)):
                AzureOpenAIProvider(config)

    @patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI')
    def test_azure_openai_provider_generate_response(self, mock_azure_openai_class):
        """Test Azure OpenAI provider generate_response method."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key"
        )
        
        # Mock the Azure OpenAI client and response
        mock_client = Mock()
        mock_azure_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response from Azure OpenAI"
        mock_client.chat.completions.create.return_value = mock_response
        
        provider = AzureOpenAIProvider(config)
        response = provider.generate_response("Test prompt")
        
        # Verify the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == "gpt-4-deployment"  # Should use deployment name
        
        assert response == "Test response from Azure OpenAI"


class TestProviderErrorHandling:
    """Test error handling across providers."""

    @patch('azurefunctions.agents.model_providers.openai_provider.OpenAI')
    def test_openai_provider_api_error_handling(self, mock_openai_class):
        """Test OpenAI provider handles API errors."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Simulate API error
        from openai import APIError
        mock_client.chat.completions.create.side_effect = APIError("API Error", response=Mock(), body="Error details")
        
        provider = OpenAIProvider(config)
        
        with pytest.raises(APIError):
            provider.generate_response("Test prompt")

    @patch('azurefunctions.agents.model_providers.openai_provider.OpenAI')
    def test_openai_provider_rate_limit_handling(self, mock_openai_class):
        """Test OpenAI provider handles rate limit errors."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-key"
        )
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Simulate rate limit error
        from openai import RateLimitError
        mock_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded", response=Mock(), body="Rate limit details")
        
        provider = OpenAIProvider(config)
        
        with pytest.raises(RateLimitError):
            provider.generate_response("Test prompt")

    def test_provider_import_error_handling(self):
        """Test provider handles missing dependency imports."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            api_key="test-key"
        )
        
        # Test when anthropic package is not installed
        with patch.dict('sys.modules', {'anthropic': None}):
            with pytest.raises(ImportError):
                from azurefunctions.agents.model_providers.anthropic_provider import AnthropicProvider
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
            extra_body={"custom_param": "value"}
        )
        
        with patch('azurefunctions.agents.model_providers.openai_provider.OpenAI') as mock_openai:
            provider = OpenAIProvider(config)
            
            # Verify configuration parameters are passed
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['timeout'] == 60
            assert call_kwargs['max_retries'] == 5
            assert call_kwargs['default_headers'] == {"X-Custom": "header"}

    def test_azure_openai_provider_api_version_handling(self):
        """Test Azure OpenAI provider API version handling."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key",
            api_version="2024-02-01"
        )
        
        with patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI') as mock_azure_openai:
            provider = AzureOpenAIProvider(config)
            
            call_kwargs = mock_azure_openai.call_args[1]
            assert call_kwargs['api_version'] == "2024-02-01"

    def test_provider_model_name_mapping(self):
        """Test that providers correctly map model names."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_key="test-key"
        )
        
        with patch('azurefunctions.agents.model_providers.azure_openai_provider.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response
            
            provider = AzureOpenAIProvider(config)
            provider.generate_response("Test")
            
            # For Azure OpenAI, model should be the deployment name
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs['model'] == "gpt-4-deployment"
