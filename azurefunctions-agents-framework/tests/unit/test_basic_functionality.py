"""Basic working tests for Azure Functions Agent Framework.

These tests verify core functionality and can be expanded as the codebase stabilizes.
"""

import pytest
from azurefunctions.agents import Agent, AgentFunctionApp, LLMConfig, LLMProvider
from azurefunctions.agents.types import AgentMode


class TestBasicFunctionality:
    """Test basic framework functionality."""

    def test_agent_creation(self, mock_llm_config):
        """Test basic agent creation."""
        agent = Agent(
            name="test_agent",
            instructions="You are a test agent",
            llm_config=mock_llm_config
        )
        assert agent.name == "test_agent"
        assert agent.instructions == "You are a test agent"
        assert agent.llm_config == mock_llm_config

    def test_agent_function_app_creation(self, basic_agent):
        """Test AgentFunctionApp creation."""
        app = AgentFunctionApp(
            agents=[basic_agent],
            create_triggers=False
        )
        assert len(app.agents) == 1
        assert basic_agent.name in app.agents
        assert app.mode == AgentMode.AZURE_FUNCTION_AGENT

    def test_multi_agent_app_creation(self, basic_agent, weather_agent):
        """Test multi-agent app creation."""
        app = AgentFunctionApp(
            agents=[basic_agent, weather_agent],
            create_triggers=False
        )
        assert len(app.agents) == 2
        assert basic_agent.name in app.agents
        assert weather_agent.name in app.agents

    def test_llm_config_creation(self):
        """Test LLM configuration creation."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test-key"
        )
        assert config.provider == LLMProvider.OPENAI
        assert config.model_name == "gpt-3.5-turbo"
        assert config.api_key == "test-key"

    def test_agent_with_tools(self, sample_tool, mock_llm_config):
        """Test agent creation with tools."""
        agent = Agent(
            name="tool_agent",
            instructions="You are an agent with tools",
            tools=[sample_tool],
            llm_config=mock_llm_config
        )
        # Test the public API for listing tools
        tool_names = agent.list_tools()
        assert len(tool_names) == 1
        assert "sample_tool" in tool_names
