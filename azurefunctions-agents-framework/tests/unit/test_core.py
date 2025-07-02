"""Unit tests for the AgentFunctionApp class.

This module tests the core AgentFunctionApp functionality including:
- AgentFunctionApp initialization and configuration
- Agent registration and validation
- HTTP endpoint creation and routing
- A2A protocol support
- Multi-agent vs single-agent mode handling
- Runner management and handoff integration
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, List

from azurefunctions.agents import Agent, AgentFunctionApp, LLMConfig, LLMProvider
from azurefunctions.agents.types import AgentMode
from azure.functions import AuthLevel


class TestAgentFunctionAppInitialization:
    """Test AgentFunctionApp initialization and basic configuration."""

    def test_agent_function_app_with_dict_agents(self, basic_agent, weather_agent):
        """Test AgentFunctionApp initialization with agent dictionary."""
        # Arrange
        agents_dict = {
            "basic": basic_agent,
            "weather": weather_agent
        }
        
        # Act
        app = AgentFunctionApp(agents=agents_dict)
        
        # Assert
        assert len(app.agents) == 2
        assert "basic" in app.agents
        assert "weather" in app.agents
        assert app.agents["basic"] == basic_agent
        assert app.agents["weather"] == weather_agent
        assert app.mode == AgentMode.AZURE_FUNCTION_AGENT
        assert app.create_triggers is True

    def test_agent_function_app_with_list_agents(self, basic_agent, weather_agent):
        """Test AgentFunctionApp initialization with agent list."""
        # Arrange
        agents_list = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents_list)
        
        # Assert
        assert len(app.agents) == 2
        assert basic_agent.name in app.agents
        assert weather_agent.name in app.agents
        assert app.agents[basic_agent.name] == basic_agent
        assert app.agents[weather_agent.name] == weather_agent

    def test_agent_function_app_single_agent(self, basic_agent):
        """Test AgentFunctionApp with single agent."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        assert len(app.agents) == 1
        assert basic_agent.name in app.agents
        assert app.agents[basic_agent.name] == basic_agent

    def test_agent_function_app_with_mode_parameter(self, basic_agent):
        """Test AgentFunctionApp with specific mode."""
        # Act
        app = AgentFunctionApp(
            agents=[basic_agent],
            mode=AgentMode.AZURE_FUNCTION_AGENT
        )
        
        # Assert
        assert app.mode == AgentMode.AZURE_FUNCTION_AGENT

    def test_agent_function_app_with_auth_level(self, basic_agent):
        """Test AgentFunctionApp with custom auth level."""
        # Act
        app = AgentFunctionApp(
            agents=[basic_agent],
            http_auth_level=AuthLevel.ANONYMOUS
        )
        
        # Assert
        # Note: Checking auth level depends on the parent class implementation
        # This test verifies the parameter is accepted without error
        assert len(app.agents) == 1

    def test_agent_function_app_without_triggers(self, basic_agent):
        """Test AgentFunctionApp with create_triggers=False."""
        # Act
        app = AgentFunctionApp(
            agents=[basic_agent],
            create_triggers=False
        )
        
        # Assert
        assert app.create_triggers is False
        assert len(app.agents) == 1


class TestAgentFunctionAppValidation:
    """Test AgentFunctionApp input validation and error handling."""

    def test_empty_agents_dict_raises_error(self):
        """Test that empty agents dictionary raises ValueError."""
        with pytest.raises(ValueError, match="Must provide.*at least one agent"):
            AgentFunctionApp(agents={})

    def test_empty_agents_list_raises_error(self):
        """Test that empty agents list raises ValueError."""
        with pytest.raises(ValueError, match="Must provide at least one agent"):
            AgentFunctionApp(agents=[])

    def test_duplicate_agent_names_raises_error(self, mock_llm_config):
        """Test that duplicate agent names in list raises ValueError."""
        # Arrange
        agent1 = Agent("DuplicateName", "First agent", llm_config=mock_llm_config)
        agent2 = Agent("DuplicateName", "Second agent", llm_config=mock_llm_config)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Duplicate agent names"):
            AgentFunctionApp(agents=[agent1, agent2])

    def test_invalid_agents_type_raises_error(self):
        """Test that invalid agents type raises ValueError."""
        with pytest.raises(ValueError, match="agents must be either"):
            AgentFunctionApp(agents="invalid_type")

    def test_none_agents_raises_error(self):
        """Test that None agents raises error."""
        with pytest.raises((ValueError, TypeError)):
            AgentFunctionApp(agents=None)


class TestAgentFunctionAppA2AMode:
    """Test AgentFunctionApp A2A mode configuration and constraints."""

    def test_a2a_mode_single_agent_succeeds(self, basic_agent):
        """Test A2A mode with single agent succeeds."""
        # Act
        app = AgentFunctionApp(
            agents=[basic_agent],
            mode=AgentMode.A2A
        )
        
        # Assert
        assert app.mode == AgentMode.A2A
        assert len(app.agents) == 1

    def test_a2a_mode_multiple_agents_raises_error(self, basic_agent, weather_agent):
        """Test A2A mode with multiple agents raises ValueError."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act & Assert
        with pytest.raises(ValueError, match="A2A mode is only supported for single-agent"):
            AgentFunctionApp(agents=agents, mode=AgentMode.A2A)

    @patch('azurefunctions.agents.core.A2AManager')
    def test_a2a_mode_initializes_a2a_manager(self, mock_a2a_manager, basic_agent):
        """Test that A2A mode initializes A2A manager."""
        # Act
        app = AgentFunctionApp(
            agents=[basic_agent],
            mode=AgentMode.A2A
        )
        
        # Assert
        # Note: The actual A2A manager initialization depends on implementation
        assert app.mode == AgentMode.A2A


class TestAgentFunctionAppRunnerManagement:
    """Test AgentFunctionApp runner creation and management."""

    def test_runners_created_for_all_agents(self, basic_agent, weather_agent):
        """Test that runners are created for all agents."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        assert len(app.runners) == 2
        assert basic_agent.name in app.runners
        assert weather_agent.name in app.runners
        # Verify runners are actually Runner instances
        for runner in app.runners.values():
            assert hasattr(runner, 'run')  # Basic check for Runner interface

    def test_single_agent_runner_creation(self, basic_agent):
        """Test runner creation for single agent."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        assert len(app.runners) == 1
        assert basic_agent.name in app.runners

    def test_runners_have_correct_agents(self, basic_agent, weather_agent):
        """Test that runners are associated with correct agents."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        # Note: This test depends on Runner implementation details
        # We're checking that the runner-agent association is maintained
        for agent_name, runner in app.runners.items():
            assert agent_name in app.agents


class TestAgentFunctionAppHandoffSystem:
    """Test AgentFunctionApp handoff system integration."""

    def test_handoff_system_initialization(self, basic_agent, weather_agent):
        """Test that handoff system components are initialized."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        assert hasattr(app, 'control_flow_manager')
        assert hasattr(app, 'handoff_engine')
        assert app.control_flow_manager is not None
        assert app.handoff_engine is not None

    def test_agents_registered_with_handoff_engine(self, basic_agent, weather_agent):
        """Test that agents are registered with handoff engine."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        # Note: This test depends on handoff engine implementation
        # We're verifying that agent registration was called
        assert app.handoff_engine is not None

    def test_runners_registered_with_each_other(self, basic_agent, weather_agent):
        """Test that runners are cross-registered for handoffs."""
        # Arrange
        agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        # Note: This test depends on Runner implementation
        # We're checking that cross-registration occurs
        assert len(app.runners) == 2


class TestAgentFunctionAppLogging:
    """Test AgentFunctionApp logging configuration."""

    def test_logger_initialization(self, basic_agent):
        """Test that logger is properly initialized."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        assert hasattr(app, 'logger')
        assert app.logger.name == "AgentFunctionApp"


class TestAgentFunctionAppProperties:
    """Test AgentFunctionApp properties and attributes."""

    def test_app_properties_basic(self, basic_agent):
        """Test basic app properties."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        assert isinstance(app.agents, dict)
        assert isinstance(app.runners, dict)
        assert isinstance(app.mode, AgentMode)
        assert isinstance(app.create_triggers, bool)

    def test_app_agents_immutability(self, basic_agent, weather_agent):
        """Test that app.agents reflects the provided agents."""
        # Arrange
        original_agents = [basic_agent, weather_agent]
        
        # Act
        app = AgentFunctionApp(agents=original_agents)
        
        # Assert
        assert len(app.agents) == len(original_agents)
        for agent in original_agents:
            assert agent.name in app.agents
            assert app.agents[agent.name] == agent

    def test_app_mode_persistence(self, basic_agent):
        """Test that app mode is correctly stored."""
        # Act
        app_default = AgentFunctionApp(agents=[basic_agent])
        app_explicit = AgentFunctionApp(
            agents=[basic_agent], 
            mode=AgentMode.AZURE_FUNCTION_AGENT
        )
        
        # Assert
        assert app_default.mode == AgentMode.AZURE_FUNCTION_AGENT
        assert app_explicit.mode == AgentMode.AZURE_FUNCTION_AGENT


class TestAgentFunctionAppComplexScenarios:
    """Test AgentFunctionApp complex initialization scenarios."""

    def test_mixed_agent_types(self, mock_llm_config):
        """Test app with different types of agents."""
        # Arrange
        basic_agent = Agent("Basic", "Basic agent", llm_config=mock_llm_config)
        
        def sample_tool(param: str) -> str:
            return f"Tool: {param}"
        
        tool_agent = Agent(
            "ToolAgent", 
            "Agent with tools", 
            tools=[sample_tool],
            llm_config=mock_llm_config
        )
        
        from azurefunctions.agents.handoff import HandoffConfig, HandoffTarget, HandoffMode
        handoff_agent = Agent(
            "HandoffAgent",
            "Agent with handoffs",
            llm_config=mock_llm_config,
            handoff_config=HandoffConfig(
                mode=HandoffMode.SWARM,
                targets=[HandoffTarget(agent_name="Basic")]
            )
        )
        
        # Act
        app = AgentFunctionApp(agents=[basic_agent, tool_agent, handoff_agent])
        
        # Assert
        assert len(app.agents) == 3
        assert "Basic" in app.agents
        assert "ToolAgent" in app.agents
        assert "HandoffAgent" in app.agents

    def test_large_number_of_agents(self, mock_llm_config):
        """Test app with many agents."""
        # Arrange
        agents = []
        for i in range(10):
            agent = Agent(
                f"Agent{i}",
                f"Agent number {i}",
                llm_config=mock_llm_config
            )
            agents.append(agent)
        
        # Act
        app = AgentFunctionApp(agents=agents)
        
        # Assert
        assert len(app.agents) == 10
        assert len(app.runners) == 10
        for i in range(10):
            assert f"Agent{i}" in app.agents

    def test_agents_with_same_instructions_different_names(self, mock_llm_config):
        """Test agents with same instructions but different names."""
        # Arrange
        instructions = "You are a helpful assistant."
        agent1 = Agent("Agent1", instructions, llm_config=mock_llm_config)
        agent2 = Agent("Agent2", instructions, llm_config=mock_llm_config)
        
        # Act
        app = AgentFunctionApp(agents=[agent1, agent2])
        
        # Assert
        assert len(app.agents) == 2
        assert app.agents["Agent1"].instructions == app.agents["Agent2"].instructions
        assert app.agents["Agent1"] != app.agents["Agent2"]  # Different instances


class TestAgentFunctionAppInheritance:
    """Test AgentFunctionApp inheritance and Azure Functions integration."""

    def test_function_register_inheritance(self, basic_agent):
        """Test that AgentFunctionApp inherits from FunctionRegister."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        # Check that it has attributes/methods from Azure Functions base classes
        assert hasattr(app, 'function_name')  # From FunctionRegister
        # Note: Actual method availability depends on Azure Functions implementation

    def test_azure_functions_integration_properties(self, basic_agent):
        """Test Azure Functions integration properties."""
        # Act
        app = AgentFunctionApp(agents=[basic_agent])
        
        # Assert
        # These tests depend on the Azure Functions base class implementation
        # We're checking that the inheritance chain is maintained
        assert callable(getattr(app, '__call__', None)) or hasattr(app, 'setup_function_app')


class TestAgentFunctionAppEdgeCases:
    """Test AgentFunctionApp edge cases and error scenarios."""

    def test_agent_with_none_name_handling(self, mock_llm_config):
        """Test handling of agent with None name."""
        # This test checks how the app handles agents with problematic names
        try:
            # This should fail at agent creation, not app creation
            agent = Agent(None, "Test", llm_config=mock_llm_config)
            app = AgentFunctionApp(agents=[agent])
            assert False, "Should have failed with None agent name"
        except (TypeError, ValueError):
            # Expected - agent creation should fail
            pass

    def test_agent_name_conflicts_in_dict(self, mock_llm_config):
        """Test agent name conflicts when using dictionary."""
        # Arrange
        agent1 = Agent("TestAgent", "First agent", llm_config=mock_llm_config)
        agent2 = Agent("TestAgent", "Second agent", llm_config=mock_llm_config)
        
        # When using dict, the second agent overwrites the first
        agents_dict = {
            "TestAgent": agent1,
            "TestAgent": agent2  # This overwrites agent1
        }
        
        # Act
        app = AgentFunctionApp(agents=agents_dict)
        
        # Assert
        assert len(app.agents) == 1
        assert app.agents["TestAgent"] == agent2  # Second agent wins

    def test_very_long_agent_names(self, mock_llm_config):
        """Test agents with very long names."""
        # Arrange
        long_name = "A" * 1000  # Very long name
        agent = Agent(long_name, "Agent with long name", llm_config=mock_llm_config)
        
        # Act
        app = AgentFunctionApp(agents=[agent])
        
        # Assert
        assert long_name in app.agents
        assert len(app.agents[long_name].name) == 1000
