"""Unit tests for Azure Functions Agent Framework types module.

This module tests the core type definitions, data structures, and enumerations
used throughout the framework.
"""

from datetime import datetime, timezone

from azurefunctions.agents.handoff.types import HandoffConfig
from azurefunctions.agents.handoff.types import HandoffMode as HandoffType
from azurefunctions.agents.types import (
    AgentMode,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LLMConfig,
    LLMProvider,
    MCPConfig,
    MCPServerMode,
    ToolDefinition,
    TriggerType,
)


class TestEnumDefinitions:
    """Test enum type definitions."""

    def test_agent_mode_values(self):
        """Test AgentMode enum values."""
        assert AgentMode.AZURE_FUNCTION_AGENT.value == "azure_function_agent"
        assert AgentMode.A2A.value == "a2a"
        assert len(AgentMode) == 2

    def test_trigger_type_values(self):
        """Test TriggerType enum values."""
        assert TriggerType.HTTP_ROUTE.value == "http_route"
        assert TriggerType.TIMER.value == "timer"
        assert len(TriggerType) == 2

    def test_llm_provider_values(self):
        """Test LLMProvider enum values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.GOOGLE.value == "google"
        assert LLMProvider.OLLAMA.value == "ollama"
        assert LLMProvider.AZURE_AI.value == "azure_ai"
        assert len(LLMProvider) == 6

    def test_mcp_server_mode_values(self):
        """Test MCPServerMode enum values."""
        assert MCPServerMode.STDIO.value == "stdio"
        assert MCPServerMode.SSE.value == "sse"
        assert MCPServerMode.STREAMABLE_HTTP.value == "streamable_http"
        assert len(MCPServerMode) == 3

    def test_handoff_type_values(self):
        """Test HandoffType enum values."""
        assert HandoffType.SWARM.value == "swarm"
        assert HandoffType.COORDINATOR.value == "coordinator"
        assert HandoffType.CONDITIONAL.value == "conditional"
        assert len(HandoffType) == 3


class TestLLMConfig:
    """Test LLMConfig dataclass."""

    def test_llm_config_basic_initialization(self):
        """Test basic LLMConfig initialization."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-4")

        assert config.provider == LLMProvider.OPENAI
        assert config.model_name == "gpt-4"
        assert config.api_key is None
        assert config.api_base is None
        assert config.temperature == 0.7
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_llm_config_full_initialization(self):
        """Test LLMConfig with all parameters."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            api_key="test-key",
            api_base="https://api.openai.com",
            api_version="2023-12-01-preview",
            organization="test-org",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
            max_retries=5,
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            extra_headers={"X-Custom": "test"},
            extra_body={"custom": "value"},
        )

        assert config.provider == LLMProvider.AZURE_OPENAI
        assert config.model_name == "gpt-4"
        assert config.api_key == "test-key"
        assert config.api_base == "https://api.openai.com"
        assert config.api_version == "2023-12-01-preview"
        assert config.organization == "test-org"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.azure_endpoint == "https://test.openai.azure.com"
        assert config.azure_deployment == "gpt-4-deployment"
        assert config.extra_headers == {"X-Custom": "test"}
        assert config.extra_body == {"custom": "value"}

    def test_llm_config_openai_defaults(self):
        """Test OpenAI specific LLMConfig defaults."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI, model_name="gpt-3.5-turbo", api_key="sk-test"
        )

        assert config.azure_endpoint is None
        assert config.azure_deployment is None
        assert config.api_version is None

    def test_llm_config_azure_openai_settings(self):
        """Test Azure OpenAI specific settings."""
        config = LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model_name="gpt-4",
            azure_endpoint="https://test.openai.azure.com",
            azure_deployment="gpt-4-deployment",
            api_version="2023-12-01-preview",
        )

        assert config.azure_endpoint == "https://test.openai.azure.com"
        assert config.azure_deployment == "gpt-4-deployment"
        assert config.api_version == "2023-12-01-preview"


class TestChatMessage:
    """Test ChatMessage dataclass."""

    def test_chat_message_basic(self):
        """Test basic ChatMessage creation."""
        message = ChatMessage(role="user", content="Hello, world!")

        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.tool_calls is None
        assert message.tool_call_id is None
        assert message.name is None

    def test_chat_message_system(self):
        """Test system ChatMessage."""
        message = ChatMessage(role="system", content="You are a helpful assistant.")

        assert message.role == "system"
        assert message.content == "You are a helpful assistant."

    def test_chat_message_assistant_with_tools(self):
        """Test assistant ChatMessage with tool calls."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"city": "San Francisco"}',
                },
            }
        ]

        message = ChatMessage(
            role="assistant",
            content="I'll get the weather for you.",
            tool_calls=tool_calls,
        )

        assert message.role == "assistant"
        assert message.content == "I'll get the weather for you."
        assert message.tool_calls == tool_calls

    def test_chat_message_tool_response(self):
        """Test tool response ChatMessage."""
        message = ChatMessage(
            role="tool",
            content='{"temperature": 72, "condition": "sunny"}',
            tool_call_id="call_1",
            name="get_weather",
        )

        assert message.role == "tool"
        assert message.content == '{"temperature": 72, "condition": "sunny"}'
        assert message.tool_call_id == "call_1"
        assert message.name == "get_weather"


class TestToolDefinition:
    """Test ToolDefinition dataclass."""

    def test_tool_definition_basic(self):
        """Test basic ToolDefinition creation."""

        def sample_tool(text: str) -> str:
            return f"Processed: {text}"

        tool = ToolDefinition(
            name="sample_tool",
            description="A sample tool for testing",
            function=sample_tool,
        )

        assert tool.name == "sample_tool"
        assert tool.description == "A sample tool for testing"
        assert tool.function == sample_tool
        assert tool.parameters is None
        assert tool.required_params is None

    def test_tool_definition_with_parameters(self):
        """Test ToolDefinition with parameters."""

        def weather_tool(city: str, units: str = "celsius") -> str:
            return f"Weather in {city} ({units})"

        parameters = {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
        }

        tool = ToolDefinition(
            name="get_weather",
            description="Get weather information for a city",
            function=weather_tool,
            parameters=parameters,
            required_params=["city"],
        )

        assert tool.name == "get_weather"
        assert tool.description == "Get weather information for a city"
        assert tool.function == weather_tool
        assert tool.parameters == parameters
        assert tool.required_params == ["city"]

    async def test_tool_definition_async_function(self):
        """Test ToolDefinition with async function."""

        async def async_tool(data: str) -> str:
            return f"Async processed: {data}"

        tool = ToolDefinition(
            name="async_tool", description="An async tool", function=async_tool
        )

        assert tool.name == "async_tool"
        assert tool.function == async_tool

        # Test that we can call the async function
        result = await tool.function("test")
        assert result == "Async processed: test"


class TestMCPConfig:
    """Test MCPConfig dataclass."""

    def test_mcp_config_defaults(self):
        """Test MCPConfig default values."""
        config = MCPConfig()

        assert config.enabled is True
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_mcp_config_custom_values(self):
        """Test MCPConfig with custom values."""
        config = MCPConfig(enabled=False, timeout=60, max_retries=5)

        assert config.enabled is False
        assert config.timeout == 60
        assert config.max_retries == 5


class TestChatRequest:
    """Test ChatRequest dataclass."""

    def test_chat_request_string_message(self):
        """Test ChatRequest with string message."""
        request = ChatRequest(message="Hello, AI!", session_id="session_123")

        assert request.message == "Hello, AI!"
        assert request.session_id == "session_123"
        assert request.context == {}
        assert request.tools is None

    def test_chat_request_with_context(self):
        """Test ChatRequest with context."""
        context = {"user_id": "user123", "preferences": {"language": "en"}}

        request = ChatRequest(
            message="What's the weather like?",
            session_id="session_456",
            context=context,
        )

        assert request.message == "What's the weather like?"
        assert request.session_id == "session_456"
        assert request.context == context

    def test_chat_request_with_tools(self):
        """Test ChatRequest with tool specifications."""
        tools = ["get_weather", "search_web"]

        request = ChatRequest(
            message="Help me plan my day", session_id="session_789", tools=tools
        )

        assert request.message == "Help me plan my day"
        assert request.session_id == "session_789"
        assert request.tools == tools


class TestChatResponse:
    """Test ChatResponse dataclass."""

    def test_chat_response_basic(self):
        """Test basic ChatResponse creation."""
        response = ChatResponse(
            message="Hello! How can I help you today?", session_id="session_123"
        )

        assert response.message == "Hello! How can I help you today?"
        assert response.session_id == "session_123"
        assert response.tool_calls is None
        assert response.metadata == {}
        assert isinstance(response.timestamp, datetime)

    def test_chat_response_with_tool_calls(self):
        """Test ChatResponse with tool calls."""
        tool_calls = [
            {
                "id": "call_1",
                "function": "get_weather",
                "arguments": {"city": "San Francisco"},
            }
        ]

        response = ChatResponse(
            message="I'll check the weather for you.",
            session_id="session_456",
            tool_calls=tool_calls,
        )

        assert response.message == "I'll check the weather for you."
        assert response.session_id == "session_456"
        assert response.tool_calls == tool_calls

    def test_chat_response_with_metadata(self):
        """Test ChatResponse with metadata."""
        metadata = {"model": "gpt-4", "tokens_used": 150, "response_time": 1.23}

        response = ChatResponse(
            message="Response with metadata",
            session_id="session_789",
            metadata=metadata,
        )

        assert response.message == "Response with metadata"
        assert response.session_id == "session_789"
        assert response.metadata == metadata

    def test_chat_response_timestamp_generation(self):
        """Test that ChatResponse generates timestamp correctly."""
        before_creation = datetime.now(timezone.utc)
        response = ChatResponse(message="Test message", session_id="test_session")
        after_creation = datetime.now(timezone.utc)

        assert before_creation <= response.timestamp <= after_creation
        assert response.timestamp.tzinfo == timezone.utc


class TestHandoffConfig:
    """Test HandoffConfig dataclass."""

    def test_handoff_config_swarm(self):
        """Test HandoffConfig for swarm handoff."""
        config = HandoffConfig(
            handoff_type=HandoffType.SWARM,
            target_agents=["agent1", "agent2"],
            instructions="Hand off to the appropriate specialist",
        )

        assert config.handoff_type == HandoffType.SWARM
        assert config.target_agents == ["agent1", "agent2"]
        assert config.instructions == "Hand off to the appropriate specialist"
        assert config.conditions is None

    def test_handoff_config_coordinator(self):
        """Test HandoffConfig for coordinator handoff."""
        config = HandoffConfig(
            handoff_type=HandoffType.COORDINATOR,
            target_agents=["coordinator"],
            instructions="Route to coordinator for task delegation",
        )

        assert config.handoff_type == HandoffType.COORDINATOR
        assert config.target_agents == ["coordinator"]
        assert config.instructions == "Route to coordinator for task delegation"

    def test_handoff_config_conditional(self):
        """Test HandoffConfig for conditional handoff."""
        conditions = {"user_intent": "technical_support", "complexity": "high"}

        config = HandoffConfig(
            handoff_type=HandoffType.CONDITIONAL,
            target_agents=["tech_support_agent"],
            instructions="Hand off for technical support",
            conditions=conditions,
        )

        assert config.handoff_type == HandoffType.CONDITIONAL
        assert config.target_agents == ["tech_support_agent"]
        assert config.instructions == "Hand off for technical support"
        assert config.conditions == conditions


class TestTypeValidation:
    """Test type validation and edge cases."""

    def test_llm_config_invalid_provider(self):
        """Test LLMConfig with invalid provider type."""
        # This would be caught by type checker, but test runtime behavior
        config = LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-4")

        # Should work with valid provider
        assert config.provider == LLMProvider.OPENAI

    def test_chat_message_empty_content(self):
        """Test ChatMessage with empty content."""
        message = ChatMessage(role="user", content="")

        assert message.role == "user"
        assert message.content == ""

    def test_tool_definition_callable_validation(self):
        """Test that ToolDefinition accepts callable functions."""

        def valid_tool():
            pass

        tool = ToolDefinition(name="test", description="test tool", function=valid_tool)

        assert callable(tool.function)

    def test_handoff_config_empty_target_agents(self):
        """Test HandoffConfig with empty target agents list."""
        config = HandoffConfig(
            handoff_type=HandoffType.SWARM,
            target_agents=[],
            instructions="No target agents",
        )

        assert config.target_agents == []
        assert len(config.target_agents) == 0
