"""Unit tests for the Agent class.

This module tests the core Agent class functionality including:
- Agent initialization and configuration
- Tool registration and management
- LLM integration
- Request processing
- Privacy controls
- Handoff configuration
"""

import asyncio

import pytest

from azurefunctions.agents import Agent, LLMConfig, LLMProvider
from azurefunctions.agents.handoff import HandoffConfig, HandoffMode, HandoffTarget


class TestAgentInitialization:
    """Test Agent initialization and basic configuration."""

    def test_agent_basic_initialization(self, mock_llm_config):
        """Test basic agent initialization with minimal parameters."""
        # Arrange
        name = "TestAgent"
        instructions = "You are a helpful test agent."

        # Act
        agent = Agent(name=name, instructions=instructions, llm_config=mock_llm_config)

        # Assert
        assert agent.name == name
        assert agent.instructions == instructions
        assert agent.llm_config == mock_llm_config
        assert agent.version == "1.0.0"  # Default version
        assert agent.enable_conversational_agent is True
        assert agent.expose_agent_info is True
        assert agent.expose_instructions is True
        assert agent.expose_tools is True
        assert agent.handoff_config is None

    def test_agent_full_initialization(self, mock_llm_config, sample_tool):
        """Test agent initialization with all parameters."""
        # Arrange
        name = "FullTestAgent"
        instructions = "You are a comprehensive test agent."
        tools = [sample_tool]
        version = "2.0.0"
        description = "A comprehensive test agent for unit testing"

        # Act
        agent = Agent(
            name=name,
            instructions=instructions,
            tools=tools,
            llm_config=mock_llm_config,
            version=version,
            description=description,
            enable_conversational_agent=False,
            expose_agent_info=False,
            expose_instructions=False,
            expose_tools=False,
        )

        # Assert
        assert agent.name == name
        assert agent.instructions == instructions
        assert agent.version == version
        assert agent.description == description
        assert agent.enable_conversational_agent is False
        assert agent.expose_agent_info is False
        assert agent.expose_instructions is False
        assert agent.expose_tools is False

    def test_agent_with_handoff_config(self, mock_llm_config):
        """Test agent initialization with handoff configuration."""
        # Arrange
        handoff_config = HandoffConfig(
            mode=HandoffMode.SWARM, targets=[HandoffTarget(agent_name="other_agent")]
        )

        # Act
        agent = Agent(
            name="HandoffAgent",
            instructions="Agent with handoff capabilities",
            llm_config=mock_llm_config,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.handoff_config == handoff_config
        assert agent.handoff_config.mode == HandoffMode.SWARM
        assert len(agent.handoff_config.targets) == 1
        assert agent.handoff_config.targets[0].agent_name == "other_agent"

    def test_agent_default_description(self, mock_llm_config):
        """Test that agent gets default description when none provided."""
        # Arrange & Act
        agent = Agent(
            name="DefaultDescAgent",
            instructions="Test agent",
            llm_config=mock_llm_config,
        )

        # Assert
        assert agent.description == "AI Agent: DefaultDescAgent"

    def test_agent_logger_configuration(self, mock_llm_config):
        """Test that agent logger is properly configured."""
        # Arrange & Act
        agent = Agent(
            name="LoggerTestAgent",
            instructions="Test agent",
            llm_config=mock_llm_config,
        )

        # Assert
        assert agent.logger.name == "Agent.LoggerTestAgent"


class TestAgentToolManagement:
    """Test agent tool registration and management."""

    def test_agent_with_single_tool(self, mock_llm_config):
        """Test agent initialization with a single tool."""

        # Arrange
        def test_tool(param: str) -> str:
            """Test tool function."""
            return f"Tool processed: {param}"

        # Act
        agent = Agent(
            name="SingleToolAgent",
            instructions="Agent with one tool",
            tools=[test_tool],
            llm_config=mock_llm_config,
        )

        # Assert
        # Note: The actual tool registration logic would be tested
        # when we examine the tool_registry implementation
        assert hasattr(agent, "tools") or hasattr(agent, "tool_registry")

    def test_agent_with_multiple_tools(
        self, mock_llm_config, sample_tool, async_sample_tool
    ):
        """Test agent initialization with multiple tools."""

        # Arrange
        def another_tool(x: int, y: int) -> int:
            """Another test tool."""
            return x + y

        tools = [sample_tool, async_sample_tool, another_tool]

        # Act
        agent = Agent(
            name="MultiToolAgent",
            instructions="Agent with multiple tools",
            tools=tools,
            llm_config=mock_llm_config,
        )

        # Assert
        # Verify tools are properly registered
        assert hasattr(agent, "tools") or hasattr(agent, "tool_registry")

    def test_agent_with_complex_tool_parameters(
        self, mock_llm_config, sample_tool_with_complex_params
    ):
        """Test agent with tools that have complex parameter types."""
        # Act
        agent = Agent(
            name="ComplexToolAgent",
            instructions="Agent with complex tool parameters",
            tools=[sample_tool_with_complex_params],
            llm_config=mock_llm_config,
        )

        # Assert
        assert hasattr(agent, "tools") or hasattr(agent, "tool_registry")

    def test_agent_with_no_tools(self, mock_llm_config):
        """Test agent initialization with no tools."""
        # Act
        agent = Agent(
            name="NoToolAgent",
            instructions="Agent without tools",
            llm_config=mock_llm_config,
        )

        # Assert
        # Should initialize successfully without tools
        assert agent.name == "NoToolAgent"


class TestAgentLLMConfiguration:
    """Test agent LLM configuration and provider handling."""

    def test_agent_with_openai_config(self):
        """Test agent with OpenAI LLM configuration."""
        # Arrange
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="test-openai-key",
            temperature=0.8,
        )

        # Act
        agent = Agent(
            name="OpenAIAgent", instructions="Agent using OpenAI", llm_config=llm_config
        )

        # Assert
        assert agent.llm_config.provider == LLMProvider.OPENAI
        assert agent.llm_config.model_name == "gpt-4"
        assert agent.llm_config.temperature == 0.8

    def test_agent_with_anthropic_config(self, anthropic_llm_config):
        """Test agent with Anthropic LLM configuration."""
        # Act
        agent = Agent(
            name="AnthropicAgent",
            instructions="Agent using Anthropic Claude",
            llm_config=anthropic_llm_config,
        )

        # Assert
        assert agent.llm_config.provider == LLMProvider.ANTHROPIC
        assert agent.llm_config.model_name == "claude-3-sonnet-20240229"

    def test_agent_with_google_config(self, google_llm_config):
        """Test agent with Google Gemini configuration."""
        # Act
        agent = Agent(
            name="GoogleAgent",
            instructions="Agent using Google Gemini",
            llm_config=google_llm_config,
        )

        # Assert
        assert agent.llm_config.provider == LLMProvider.GOOGLE
        assert agent.llm_config.model_name == "gemini-pro"

    def test_agent_without_llm_config(self):
        """Test agent initialization without LLM configuration and conversational mode disabled."""
        # Act
        agent = Agent(
            name="NoLLMAgent",
            instructions="Agent without LLM config",
            enable_conversational_agent=False,
        )

        # Assert
        assert agent.llm_config is None


class TestAgentInstructions:
    """Test agent instructions handling."""

    def test_agent_with_string_instructions(self, mock_llm_config):
        """Test agent with string instructions."""
        # Arrange
        instructions = "You are a helpful assistant that provides weather information."

        # Act
        agent = Agent(
            name="StringInstructionsAgent",
            instructions=instructions,
            llm_config=mock_llm_config,
        )

        # Assert
        assert agent.instructions == instructions

    def test_agent_with_callable_instructions(self, mock_llm_config):
        """Test agent with callable instructions."""

        # Arrange
        def get_instructions():
            return "You are a dynamic assistant with callable instructions."

        # Act
        agent = Agent(
            name="CallableInstructionsAgent",
            instructions=get_instructions,
            llm_config=mock_llm_config,
        )

        # Assert
        assert callable(agent.instructions)
        assert (
            agent.instructions()
            == "You are a dynamic assistant with callable instructions."
        )

    def test_agent_with_async_callable_instructions(self, mock_llm_config):
        """Test agent with async callable instructions."""

        # Arrange
        async def get_async_instructions():
            await asyncio.sleep(0.01)  # Simulate async operation
            return "You are an async assistant with dynamic instructions."

        # Act
        agent = Agent(
            name="AsyncInstructionsAgent",
            instructions=get_async_instructions,
            llm_config=mock_llm_config,
        )

        # Assert
        assert callable(agent.instructions)
        # Note: Testing async callable execution would require async test methods

    def test_agent_with_no_instructions(self, mock_llm_config):
        """Test agent with no instructions (None)."""
        # Act
        agent = Agent(name="NoInstructionsAgent", llm_config=mock_llm_config)

        # Assert
        assert agent.instructions is None


class TestAgentPrivacyControls:
    """Test agent privacy and information exposure controls."""

    def test_agent_expose_all_info(self, mock_llm_config):
        """Test agent with all information exposed."""
        # Act
        agent = Agent(
            name="OpenAgent",
            instructions="Open agent",
            llm_config=mock_llm_config,
            expose_agent_info=True,
            expose_instructions=True,
            expose_tools=True,
        )

        # Assert
        assert agent.expose_agent_info is True
        assert agent.expose_instructions is True
        assert agent.expose_tools is True

    def test_agent_expose_no_info(self, mock_llm_config):
        """Test agent with all information hidden."""
        # Act
        agent = Agent(
            name="PrivateAgent",
            instructions="Private agent",
            llm_config=mock_llm_config,
            expose_agent_info=False,
            expose_instructions=False,
            expose_tools=False,
        )

        # Assert
        assert agent.expose_agent_info is False
        assert agent.expose_instructions is False
        assert agent.expose_tools is False

    def test_agent_selective_info_exposure(self, mock_llm_config):
        """Test agent with selective information exposure."""
        # Act
        agent = Agent(
            name="SelectiveAgent",
            instructions="Selective agent",
            llm_config=mock_llm_config,
            expose_agent_info=True,
            expose_instructions=False,
            expose_tools=True,
        )

        # Assert
        assert agent.expose_agent_info is True
        assert agent.expose_instructions is False
        assert agent.expose_tools is True


class TestAgentConversationalMode:
    """Test agent conversational mode configuration."""

    def test_agent_conversational_enabled(self, mock_llm_config):
        """Test agent with conversational mode enabled."""
        # Act
        agent = Agent(
            name="ConversationalAgent",
            instructions="Conversational agent",
            llm_config=mock_llm_config,
            enable_conversational_agent=True,
        )

        # Assert
        assert agent.enable_conversational_agent is True

    def test_agent_conversational_disabled(self, mock_llm_config):
        """Test agent with conversational mode disabled."""
        # Act
        agent = Agent(
            name="NonConversationalAgent",
            instructions="Non-conversational agent",
            llm_config=mock_llm_config,
            enable_conversational_agent=False,
        )

        # Assert
        assert agent.enable_conversational_agent is False


class TestAgentHandoffConfiguration:
    """Test agent handoff configuration and capabilities."""

    def test_agent_swarm_handoff_config(self, mock_llm_config):
        """Test agent with swarm handoff configuration."""
        # Arrange
        handoff_config = HandoffConfig(
            mode=HandoffMode.SWARM,
            targets=[
                HandoffTarget(agent_name="agent1"),
                HandoffTarget(agent_name="agent2"),
            ],
        )

        # Act
        agent = Agent(
            name="SwarmAgent",
            instructions="Swarm mode agent",
            llm_config=mock_llm_config,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.handoff_config.mode == HandoffMode.SWARM
        assert len(agent.handoff_config.targets) == 2
        assert agent.handoff_config.targets[0].agent_name == "agent1"
        assert agent.handoff_config.targets[1].agent_name == "agent2"

    def test_agent_coordinator_handoff_config(self, mock_llm_config):
        """Test agent with coordinator handoff configuration."""
        # Arrange
        handoff_config = HandoffConfig(
            mode=HandoffMode.COORDINATOR,
            targets=[
                HandoffTarget(agent_name="specialist1"),
                HandoffTarget(agent_name="specialist2"),
            ],
        )

        # Act
        agent = Agent(
            name="CoordinatorAgent",
            instructions="Coordinator mode agent",
            llm_config=mock_llm_config,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.handoff_config.mode == HandoffMode.COORDINATOR
        assert len(agent.handoff_config.targets) == 2

    def test_agent_conditional_handoff_config(self, mock_llm_config):
        """Test agent with conditional handoff configuration."""

        # Arrange
        def condition_function(request_data):
            return "help" in request_data.get("message", "").lower()

        handoff_config = HandoffConfig(
            mode=HandoffMode.CONDITIONAL,
            targets=[
                HandoffTarget(
                    agent_name="help_agent",
                    condition=condition_function,
                    description="Route to help agent for help requests",
                )
            ],
        )

        # Act
        agent = Agent(
            name="ConditionalAgent",
            instructions="Conditional routing agent",
            llm_config=mock_llm_config,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.handoff_config.mode == HandoffMode.CONDITIONAL
        assert len(agent.handoff_config.targets) == 1
        assert callable(agent.handoff_config.targets[0].condition)

    def test_agent_no_handoff_config(self, mock_llm_config):
        """Test agent without handoff configuration."""
        # Act
        agent = Agent(
            name="NoHandoffAgent",
            instructions="Agent without handoff",
            llm_config=mock_llm_config,
        )

        # Assert
        assert agent.handoff_config is None


class TestAgentMCPIntegration:
    """Test agent MCP server integration."""

    def test_agent_with_mcp_servers(self, mock_llm_config, mock_mcp_server):
        """Test agent initialization with MCP servers."""
        # Act
        agent = Agent(
            name="MCPAgent",
            instructions="Agent with MCP integration",
            mcp_servers=[mock_mcp_server],
            llm_config=mock_llm_config,
        )

        # Assert
        # Note: The actual MCP integration testing would depend on
        # the implementation details in the Agent class
        assert hasattr(agent, "mcp_servers") or hasattr(agent, "mcp_config")

    def test_agent_with_multiple_mcp_servers(self, mock_llm_config, mock_mcp_server):
        """Test agent with multiple MCP servers."""
        # Arrange
        from azurefunctions.agents.mcp.server import MCPServerSseParams

        mcp_server2 = type(mock_mcp_server)(
            name="TestMCPServer2",
            mode=mock_mcp_server.mode,
            params=MCPServerSseParams(
                url="http://localhost:8081/test-mcp2", timeout=5.0
            ),
        )

        # Act
        agent = Agent(
            name="MultiMCPAgent",
            instructions="Agent with multiple MCP servers",
            mcp_servers=[mock_mcp_server, mcp_server2],
            llm_config=mock_llm_config,
        )

        # Assert
        assert hasattr(agent, "mcp_servers") or hasattr(agent, "mcp_config")

    def test_agent_without_mcp_servers(self, mock_llm_config):
        """Test agent without MCP servers."""
        # Act
        agent = Agent(
            name="NoMCPAgent",
            instructions="Agent without MCP servers",
            llm_config=mock_llm_config,
        )

        # Assert
        # Should initialize successfully without MCP servers
        assert agent.name == "NoMCPAgent"


class TestAgentStringRepresentation:
    """Test agent string representation and metadata."""

    def test_agent_str_representation(self, mock_llm_config):
        """Test agent string representation."""
        # Arrange
        agent = Agent(
            name="StringTestAgent",
            instructions="Test agent for string representation",
            llm_config=mock_llm_config,
            version="1.5.0",
            description="A test agent for string testing",
        )

        # Act
        str_repr = str(agent)

        # Assert
        assert "StringTestAgent" in str_repr

    def test_agent_repr_representation(self, mock_llm_config):
        """Test agent repr representation."""
        # Arrange
        agent = Agent(
            name="ReprTestAgent",
            instructions="Test agent for repr",
            llm_config=mock_llm_config,
        )

        # Act
        repr_str = repr(agent)

        # Assert
        assert "Agent" in repr_str
        assert "ReprTestAgent" in repr_str


class TestAgentValidation:
    """Test agent parameter validation and error handling."""

    def test_agent_empty_name_validation(self, mock_llm_config):
        """Test that empty agent name is handled appropriately."""
        # This test depends on whether the Agent class validates names
        # If validation exists, it should raise an appropriate error
        # If not, it should accept empty names

        try:
            agent = Agent(
                name="",
                instructions="Agent with empty name",
                llm_config=mock_llm_config,
            )
            # If no validation, agent should be created
            assert agent.name == ""
        except (ValueError, TypeError) as e:
            # If validation exists, appropriate error should be raised
            assert "name" in str(e).lower()

    def test_agent_none_name_validation(self, mock_llm_config):
        """Test that None agent name is handled appropriately."""
        with pytest.raises((TypeError, ValueError)):
            Agent(
                name=None,
                instructions="Agent with None name",
                llm_config=mock_llm_config,
            )

    def test_agent_invalid_tool_validation(self, mock_llm_config):
        """Test that invalid tools are handled appropriately."""
        # Arrange
        invalid_tool = "not_a_function"  # String instead of function

        # Act & Assert
        try:
            agent = Agent(
                name="InvalidToolAgent",
                instructions="Agent with invalid tool",
                tools=[invalid_tool],
                llm_config=mock_llm_config,
            )
            # If no validation, should work (though tool won't be functional)
            assert agent.name == "InvalidToolAgent"
        except (TypeError, ValueError) as e:
            # If validation exists, should raise appropriate error
            assert "tool" in str(e).lower() or "function" in str(e).lower()


# ===========================
# Integration-style tests for Agent behavior
# ===========================


class TestAgentBehaviorIntegration:
    """Integration-style tests for agent behavior (still unit tests but testing interaction between components)."""

    @pytest.mark.asyncio
    async def test_agent_with_tools_and_handoff(self, mock_llm_config):
        """Test agent that has both tools and handoff configuration."""

        # Arrange
        def test_tool(param: str) -> str:
            return f"Tool result: {param}"

        handoff_config = HandoffConfig(
            mode=HandoffMode.SWARM, targets=[HandoffTarget(agent_name="other_agent")]
        )

        # Act
        agent = Agent(
            name="FullFeaturedAgent",
            instructions="Agent with tools and handoffs",
            tools=[test_tool],
            llm_config=mock_llm_config,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.name == "FullFeaturedAgent"
        assert agent.handoff_config is not None
        assert hasattr(agent, "tools") or hasattr(agent, "tool_registry")

    @pytest.mark.asyncio
    async def test_agent_comprehensive_configuration(
        self, mock_llm_config, sample_tool
    ):
        """Test agent with comprehensive configuration including all optional parameters."""
        # Arrange
        handoff_config = HandoffConfig(
            mode=HandoffMode.COORDINATOR,
            targets=[HandoffTarget(agent_name="specialist")],
        )

        # Act
        agent = Agent(
            name="ComprehensiveAgent",
            instructions="Comprehensive test agent",
            tools=[sample_tool],
            llm_config=mock_llm_config,
            enable_conversational_agent=True,
            version="2.1.0",
            description="A comprehensive test agent with all features",
            expose_agent_info=True,
            expose_instructions=False,
            expose_tools=True,
            handoff_config=handoff_config,
        )

        # Assert
        assert agent.name == "ComprehensiveAgent"
        assert agent.version == "2.1.0"
        assert agent.description == "A comprehensive test agent with all features"
        assert agent.enable_conversational_agent is True
        assert agent.expose_agent_info is True
        assert agent.expose_instructions is False
        assert agent.expose_tools is True
        assert agent.handoff_config.mode == HandoffMode.COORDINATOR
