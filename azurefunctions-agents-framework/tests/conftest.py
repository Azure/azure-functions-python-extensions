"""Updated pytest configuration and shared fixtures for Azure Functions Agent Framework tests.

This module provides shared pytest fixtures, configuration, and utilities
used across all test modules. Updated to match the current codebase structure.
"""

import asyncio
import os
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock

import pytest

# Import framework components for testing
from azurefunctions.agents import (
    Agent,
    AgentFunctionApp,
    LLMConfig,
    LLMProvider,
    Runner,
)
from azurefunctions.agents.types import (
    AgentMode,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolDefinition,
)
from azurefunctions.agents.handoff import (
    HandoffMode,
    HandoffStrategy,
    ControlReturn,
    HandoffTarget,
    HandoffConfig,
)

# ================================
# Pytest Configuration
# ================================


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_api_key: mark test as requiring real API keys"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# ================================
# Core Fixtures
# ================================


@pytest.fixture
def mock_llm_config():
    """Provide a mock LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test-api-key",
        temperature=0.7,
        max_tokens=150,
    )


@pytest.fixture
def mock_azure_openai_config():
    """Provide a mock Azure OpenAI configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.AZURE_OPENAI,
        model_name="gpt-35-turbo",
        api_key="test-api-key",
        azure_endpoint="https://test.openai.azure.com/",
        azure_deployment="gpt-35-turbo",
        api_version="2023-05-15",
    )


@pytest.fixture
def mock_anthropic_config():
    """Provide a mock Anthropic configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        api_key="test-anthropic-key",
        temperature=0.7,
        max_tokens=150,
    )


# ================================
# Agent Fixtures
# ================================


@pytest.fixture
def basic_agent(mock_llm_config):
    """Create a basic agent for testing."""
    agent = Agent(
        name="basic_agent",
        instructions="You are a helpful assistant for testing.",
        llm_config=mock_llm_config,
        version="1.0.0",
    )
    # Replace the llm_client with a mock to avoid HTTP client issues
    # Configure the mock to not cause async warnings
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value={"response": "Mock response"})
    agent.llm_client = mock_client
    return agent


@pytest.fixture
def weather_agent(mock_llm_config):
    """Create a weather agent with tools for testing."""

    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"The weather in {city} is sunny, 72°F"

    weather_tool = ToolDefinition(
        name="get_weather",
        description="Get current weather for a city",
        function=get_weather,
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city to get weather for"}
            },
            "required": ["city"]
        }
    )

    agent = Agent(
        name="weather_agent",
        instructions="You are a weather assistant. Use the get_weather tool to provide weather information.",
        tools=[weather_tool],
        llm_config=mock_llm_config,
        version="1.0.0",
    )
    # Replace the llm_client with a mock to avoid HTTP client issues
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value={"response": "Mock weather response"})
    agent.llm_client = mock_client
    return agent


@pytest.fixture
def calculator_agent(mock_llm_config):
    """Create a calculator agent with math tools for testing."""

    def add_numbers(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def multiply_numbers(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    add_tool = ToolDefinition(
        name="add_numbers",
        description="Add two numbers together",
        function=add_numbers,
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"]
        }
    )

    multiply_tool = ToolDefinition(
        name="multiply_numbers",
        description="Multiply two numbers",
        function=multiply_numbers,
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
            },
            "required": ["a", "b"]
        }
    )

    agent = Agent(
        name="calculator_agent",
        instructions="You are a calculator assistant. Use the available math tools to perform calculations.",
        tools=[add_tool, multiply_tool],
        llm_config=mock_llm_config,
        version="1.0.0",
    )
    # Replace the llm_client with a mock to avoid HTTP client issues
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value={"response": "Mock calculation response"})
    agent.llm_client = mock_client
    return agent


# ================================
# Tool Fixtures
# ================================


@pytest.fixture
def sample_tool():
    """Create a sample tool for testing."""
    def sample_function(input_text: str) -> str:
        """A sample function that returns processed text."""
        return f"Processed: {input_text}"

    return ToolDefinition(
        name="sample_tool",
        description="A sample tool for testing",
        function=sample_function,
        parameters={
            "type": "object",
            "properties": {
                "input_text": {"type": "string", "description": "Text to process"}
            },
            "required": ["input_text"]
        }
    )


@pytest.fixture
def async_tool():
    """Create an async tool for testing."""
    async def async_function(data: str) -> str:
        """An async function for testing."""
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Async result: {data}"

    return ToolDefinition(
        name="async_tool",
        description="An async tool for testing",
        function=async_function,
        parameters={
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to process"}
            },
            "required": ["data"]
        }
    )


# ================================
# AgentFunctionApp Fixtures
# ================================


@pytest.fixture
def single_agent_app(basic_agent):
    """Create a single-agent function app for testing."""
    return AgentFunctionApp(
        agents=[basic_agent],
        mode=AgentMode.AZURE_FUNCTION_AGENT,
        create_triggers=False  # Don't create HTTP triggers in tests
    )


@pytest.fixture
def multi_agent_app(basic_agent, weather_agent, calculator_agent):
    """Create a multi-agent function app for testing."""
    return AgentFunctionApp(
        agents=[basic_agent, weather_agent, calculator_agent],
        mode=AgentMode.AZURE_FUNCTION_AGENT,
        create_triggers=False  # Don't create HTTP triggers in tests
    )


# ================================
# Runner Fixtures
# ================================


@pytest.fixture
async def basic_runner_async(basic_agent):
    """Create a basic runner for testing with proper async cleanup."""
    runner = Runner(basic_agent)
    yield runner
    # Cleanup: ensure any pending async operations are properly handled
    if hasattr(runner.agent, 'llm_client') and hasattr(runner.agent.llm_client, 'aclose'):
        try:
            await runner.agent.llm_client.aclose()
        except:
            pass


@pytest.fixture
def basic_runner(basic_agent):
    """Create a basic runner for testing."""
    return Runner(basic_agent)


@pytest.fixture
def weather_runner(weather_agent):
    """Create a weather runner for testing."""
    return Runner(weather_agent)


# ================================
# Request/Response Fixtures
# ================================


@pytest.fixture
def sample_chat_request():
    """Create a sample chat request for testing."""
    return ChatRequest(
        message="Hello, how are you?",
        session_id="test_session_123"
    )


@pytest.fixture
def sample_messages_request():
    """Create a sample messages-based chat request for testing."""
    return ChatRequest(
        messages=[
            ChatMessage(role="user", content="What's the weather like?"),
        ],
        session_id="test_session_456"
    )


@pytest.fixture
def sample_chat_response():
    """Create a sample chat response for testing."""
    return ChatResponse(
        response="Hello! I'm doing well, thank you for asking.",
        status="success"
    )


# ================================
# Mock Fixtures
# ================================


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_client = Mock()
    mock_client.generate_response = AsyncMock(return_value="Mock LLM response")
    return mock_client


@pytest.fixture
def mock_http_request():
    """Create a mock Azure Functions HttpRequest for testing."""
    mock_request = Mock()
    mock_request.get_json.return_value = {"message": "Test message"}
    mock_request.route_params = {"agent_name": "test_agent"}
    return mock_request


# ================================
# Environment Setup
# ================================


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set test environment variables
    os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "test"

    # Clear any API keys to prevent accidental real API calls
    test_env_vars = {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_ENDPOINT": "",
    }

    # Store original values
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is not None:
            os.environ[key] = original_value
        elif key in os.environ:
            del os.environ[key]


# ================================
# Skip Conditions
# ================================


@pytest.fixture
def skip_if_no_openai_key():
    """Skip test if OpenAI API key is not available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.strip() == "":
        pytest.skip("OpenAI API key not available")


@pytest.fixture
def skip_if_no_anthropic_key():
    """Skip test if Anthropic API key is not available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.strip() == "":
        pytest.skip("Anthropic API key not available")


# ================================
# Async Helper Fixtures
# ================================


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ================================
# Test Data Fixtures
# ================================


@pytest.fixture
def sample_tool_call():
    """Sample tool call data for testing."""
    return {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": '{"city": "San Francisco"}'
        }
    }


@pytest.fixture
def sample_agent_info():
    """Sample agent info for testing."""
    return {
        "name": "test_agent",
        "description": "A test agent",
        "version": "1.0.0",
        "tools": [
            {
                "name": "sample_tool",
                "description": "A sample tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    }
                }
            }
        ]
    }


# ================================
# Additional Fixtures for Tests
# ================================

@pytest.fixture
def async_sample_tool():
    """Create an async sample tool for testing."""
    async def async_sample_function(input_text: str) -> str:
        """An async sample function that returns processed text."""
        await asyncio.sleep(0.01)  # Simulate async work
        return f"Async processed: {input_text}"

    return ToolDefinition(
        name="async_sample_tool",
        description="An async sample tool for testing",
        function=async_sample_function,
        parameters={
            "type": "object",
            "properties": {
                "input_text": {"type": "string", "description": "Text to process"}
            },
            "required": ["input_text"]
        }
    )


@pytest.fixture
def sample_tool_with_complex_params():
    """Create a tool with complex parameters for testing."""
    def complex_function(text: str, options: Dict[str, Any], count: int = 1) -> str:
        """A function with complex parameters."""
        return f"Complex result: {text} with {options} repeated {count} times"

    return ToolDefinition(
        name="complex_tool",
        description="A tool with complex parameters",
        function=complex_function,
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text"},
                "options": {
                    "type": "object",
                    "description": "Configuration options",
                    "properties": {
                        "format": {"type": "string", "enum": ["json", "xml", "plain"]},
                        "include_metadata": {"type": "boolean", "default": False}
                    }
                },
                "count": {"type": "integer", "minimum": 1, "default": 1}
            },
            "required": ["text", "options"]
        }
    )


@pytest.fixture
def anthropic_llm_config():
    """Provide an Anthropic LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        api_key="test-anthropic-key",
        temperature=0.7,
        max_tokens=150,
    )


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server for testing."""
    mock_server = Mock()
    mock_server.name = "test_mcp_server"
    mock_server.connect = AsyncMock()
    mock_server.list_tools = AsyncMock(return_value=[
        {"name": "mcp_tool", "description": "A test MCP tool"}
    ])
    mock_server.call_tool = AsyncMock(return_value="MCP tool result")
    return mock_server


@pytest.fixture
def travel_agent(mock_llm_config):
    """Create a travel agent for testing."""
    def book_flight(destination: str, departure_date: str) -> str:
        """Book a flight to a destination."""
        return f"Flight booked to {destination} on {departure_date}"

    flight_tool = ToolDefinition(
        name="book_flight",
        description="Book a flight to a destination",
        function=book_flight,
        parameters={
            "type": "object",
            "properties": {
                "destination": {"type": "string", "description": "The destination city"},
                "departure_date": {"type": "string", "description": "Departure date"}
            },
            "required": ["destination", "departure_date"]
        }
    )

    agent = Agent(
        name="travel_agent",
        instructions="You are a travel booking assistant.",
        tools=[flight_tool],
        llm_config=mock_llm_config,
        version="1.0.0",
    )
    # Replace the llm_client with a mock to avoid HTTP client issues
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.chat_completion = AsyncMock(return_value={"response": "Mock travel response"})
    agent.llm_client = mock_client
    return agent
