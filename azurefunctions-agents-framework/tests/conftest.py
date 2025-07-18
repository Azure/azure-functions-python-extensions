"""Pytest configuration and shared fixtures for Azure Functions Agent Framework tests.

This module provides shared pytest fixtures, configuration, and utilities
used across all test modules.
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
    MCPServer,
    MCPServerMode,
    Runner,
)
from azurefunctions.agents.types import ChatRequest, ChatResponse

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
# Environment and Setup Fixtures
# ================================


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment variables."""
    test_env = {
        "PYTEST_CURRENT_TEST": "true",
        "TEST_MODE": "unit",
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GOOGLE_API_KEY": "test-google-key",
    }

    # Set environment variables for testing
    for key, value in test_env.items():
        os.environ[key] = value

    yield test_env

    # Cleanup - restore original environment
    for key in test_env.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ================================
# Mock Fixtures
# ================================


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "Hello! I'm a test response from the AI agent.",
        "role": "assistant",
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22},
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response from OpenAI"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 12
    mock_response.usage.total_tokens = 22

    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test response from Claude"
    mock_response.stop_reason = "end_turn"
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 12

    mock_client.messages.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_google_client():
    """Mock Google Gemini client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "Test response from Gemini"
    mock_response.candidates = [Mock()]
    mock_response.candidates[0].finish_reason = "STOP"

    mock_client.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_azure_functions_context():
    """Mock Azure Functions context for testing."""
    mock_context = Mock()
    mock_context.invocation_id = "test-invocation-id"
    mock_context.function_name = "test-function"
    mock_context.function_directory = "/test/function/dir"
    mock_context.trace_context = Mock()
    mock_context.retry_context = Mock()
    return mock_context


@pytest.fixture
def mock_http_request():
    """Mock Azure Functions HTTP request for testing."""
    mock_request = Mock()
    mock_request.method = "POST"
    mock_request.url = "http://localhost:7071/api/test"
    mock_request.headers = {"Content-Type": "application/json"}
    mock_request.get_json.return_value = {"message": "Test message"}
    mock_request.get_body.return_value = b'{"message": "Test message"}'
    return mock_request


# ================================
# Configuration Fixtures
# ================================


@pytest.fixture
def mock_llm_config():
    """Mock LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        api_key="test-api-key",
        api_base="http://localhost:8000",  # For testing
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def anthropic_llm_config():
    """Anthropic LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        api_key="test-anthropic-key",
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def google_llm_config():
    """Google Gemini LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.GOOGLE,
        model_name="gemini-pro",
        api_key="test-google-key",
        temperature=0.7,
        max_tokens=1000,
    )


# ================================
# Tool Fixtures
# ================================


@pytest.fixture
def sample_tool():
    """Sample tool function for testing."""

    def get_weather(location: str) -> str:
        """Get weather for a location."""
        return f"The weather in {location} is sunny and 72°F."

    return get_weather


@pytest.fixture
def async_sample_tool():
    """Sample async tool function for testing."""

    async def get_weather_async(location: str) -> str:
        """Get weather for a location asynchronously."""
        await asyncio.sleep(0.1)  # Simulate async operation
        return f"The weather in {location} is sunny and 72°F."

    return get_weather_async


@pytest.fixture
def sample_tool_with_complex_params():
    """Sample tool with complex parameters for testing."""

    def search_flights(
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        class_type: str = "economy",
    ) -> Dict[str, Any]:
        """Search for flights with complex parameters."""
        return {
            "flights": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "passengers": passengers,
                    "class": class_type,
                    "price": 450.00,
                    "flight_number": "AA123",
                }
            ]
        }

    return search_flights


# ================================
# Agent Fixtures
# ================================


@pytest.fixture
def basic_agent(mock_llm_config):
    """Basic agent for testing."""
    return Agent(
        name="TestAgent",
        instructions="You are a helpful test agent.",
        llm_config=mock_llm_config,
    )


@pytest.fixture
def agent_with_tools(mock_llm_config, sample_tool, async_sample_tool):
    """Agent with tools for testing."""
    return Agent(
        name="AgentWithTools",
        instructions="You are a test agent with tools.",
        tools=[sample_tool, async_sample_tool],
        llm_config=mock_llm_config,
    )


@pytest.fixture
def weather_agent(mock_llm_config, sample_tool):
    """Weather agent for testing."""

    def get_weather(location: str) -> str:
        """Get current weather for a location."""
        return f"Weather in {location}: Sunny, 72°F"

    def get_forecast(location: str, days: int = 3) -> str:
        """Get weather forecast for a location."""
        return f"{days}-day forecast for {location}: Mostly sunny"

    return Agent(
        name="WeatherAgent",
        instructions="You provide weather information and forecasts.",
        tools=[get_weather, get_forecast],
        llm_config=mock_llm_config,
    )


@pytest.fixture
def travel_agent(mock_llm_config, sample_tool_with_complex_params):
    """Travel agent for testing."""

    def book_hotel(location: str, checkin: str, nights: int = 1) -> Dict[str, Any]:
        """Book a hotel reservation."""
        return {
            "reservation_id": "HTL123",
            "hotel": f"Test Hotel in {location}",
            "checkin": checkin,
            "nights": nights,
            "total_cost": 150.00 * nights,
        }

    return Agent(
        name="TravelAgent",
        instructions="You help with travel planning and bookings.",
        tools=[sample_tool_with_complex_params, book_hotel],
        llm_config=mock_llm_config,
    )


# ================================
# Runner Fixtures
# ================================


@pytest.fixture
def basic_runner(basic_agent):
    """Basic runner for testing."""
    return Runner(basic_agent)


@pytest.fixture
def weather_runner(weather_agent):
    """Weather agent runner for testing."""
    return Runner(weather_agent)


# ================================
# AgentFunctionApp Fixtures
# ================================


@pytest.fixture
def single_agent_app(basic_agent):
    """Single agent function app for testing."""
    return AgentFunctionApp(agents={"TestAgent": basic_agent})


@pytest.fixture
def multi_agent_app(weather_agent, travel_agent):
    """Multi-agent function app for testing."""
    return AgentFunctionApp(
        agents={"WeatherAgent": weather_agent, "TravelAgent": travel_agent}
    )


# ================================
# Request/Response Fixtures
# ================================


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return ChatRequest(
        message="Hello, how are you?",
        user_id="test-user-123",
        session_id="test-session-456",
        context={"timezone": "UTC", "language": "en"},
    )


@pytest.fixture
def sample_chat_response():
    """Sample chat response for testing."""
    return ChatResponse(
        response="Hello! I'm doing well, thank you for asking.",
        agent_name="TestAgent",
        success=True,
        context={"processed_at": "2024-01-01T00:00:00Z"},
    )


# ================================
# MCP Fixtures
# ================================


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing."""
    from azurefunctions.agents.mcp.types import MCPServerSseParams

    return MCPServer(
        name="TestMCPServer",
        mode=MCPServerMode.SSE,
        params=MCPServerSseParams(
            url="http://localhost:8080/test-mcp", timeout=5.0, sse_read_timeout=30.0
        ),
    )


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools for testing."""
    return [
        {
            "name": "mcp_weather",
            "description": "Get weather from MCP server",
            "inputSchema": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
        {
            "name": "mcp_calculator",
            "description": "Perform calculations via MCP server",
            "inputSchema": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    ]


# ================================
# Handoff Fixtures
# ================================


@pytest.fixture
def handoff_weather_agent(mock_llm_config):
    """Weather agent configured for handoff testing."""
    from azurefunctions.agents.handoff import HandoffConfig, HandoffMode, HandoffTarget

    return Agent(
        name="weather",
        instructions="You provide weather information",
        llm_config=mock_llm_config,
        handoff_config=HandoffConfig(
            mode=HandoffMode.SWARM,
            targets=[HandoffTarget(agent_name="temperature_converter")],
        ),
    )


@pytest.fixture
def handoff_temp_agent(mock_llm_config):
    """Temperature converter agent for handoff testing."""
    from azurefunctions.agents.handoff import HandoffConfig, HandoffMode, HandoffTarget

    def convert_temperature(celsius: float, target_unit: str = "fahrenheit") -> str:
        """Convert temperature between units."""
        if target_unit.lower() == "fahrenheit":
            fahrenheit = (celsius * 9 / 5) + 32
            return f"{celsius}°C = {fahrenheit}°F"
        elif target_unit.lower() == "celsius":
            return f"{celsius}°C"
        else:
            return f"Unknown unit: {target_unit}"

    return Agent(
        name="temperature_converter",
        instructions="You convert temperatures between units",
        tools=[convert_temperature],
        llm_config=mock_llm_config,
        handoff_config=HandoffConfig(
            mode=HandoffMode.SWARM, targets=[HandoffTarget(agent_name="weather")]
        ),
    )


# ================================
# Utility Fixtures
# ================================


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("Test content")
    return test_file


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "test_key": "test_value",
        "nested": {"key": "value", "list": [1, 2, 3]},
        "boolean": True,
        "number": 42,
    }


# ================================
# Async Testing Utilities
# ================================


@pytest.fixture
def run_async():
    """Utility to run async functions in tests."""

    def _run_async(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    return _run_async
