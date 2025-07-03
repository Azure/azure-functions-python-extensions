"""Unit tests for Azure Functions Agent Framework handoff system.

This module tests the multi-agent handoff capabilities including swarm,
coordinator, and conditional handoff patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from azurefunctions.agents.handoff.types import (
    HandoffMode as HandoffType, 
    HandoffConfig, 
    HandoffTarget,
    HandoffStrategy,
    ControlReturn,
    HandoffContext
)
from azurefunctions.agents.handoff.engine import HandoffEngine
from azurefunctions.agents.handoff.control_flow import ControlFlowManager
from azurefunctions.agents.handoff.types import HandoffRequest, HandoffResult, AgentResponse


class TestHandoffEngine:
    """Test the main handoff engine."""

    def test_handoff_engine_initialization(self):
        """Test HandoffEngine initialization."""
        control_flow_manager = ControlFlowManager()
        engine = HandoffEngine(control_flow_manager)
        
        assert engine._agents == {}
        assert engine.control_flow == control_flow_manager
        assert hasattr(engine, 'logger')

    def test_handoff_engine_register_agents(self):
        """Test registering agents with the handoff engine."""
        control_flow_manager = ControlFlowManager()
        engine = HandoffEngine(control_flow_manager)
        
        mock_agent1 = Mock()
        mock_agent1.name = "TestAgent1"
        mock_agent2 = Mock()
        mock_agent2.name = "TestAgent2"
        
        agents = {"TestAgent1": mock_agent1, "TestAgent2": mock_agent2}
        engine.register_agents(agents)
        
        assert engine._agents == agents

    @pytest.mark.asyncio
    async def test_handoff_engine_execute_direct_handoff(self):
        """Test executing a direct handoff."""
        control_flow_manager = ControlFlowManager()
        engine = HandoffEngine(control_flow_manager)
        
        # Create mock agents
        mock_source = Mock()
        mock_source.name = "SourceAgent"
        mock_target = Mock()
        mock_target.name = "TargetAgent"
        mock_target.process_message = AsyncMock(return_value="Handled successfully")
        
        agents = {"SourceAgent": mock_source, "TargetAgent": mock_target}
        engine.register_agents(agents)
        
        # Create handoff request
        request = HandoffRequest(
            target_agent="TargetAgent",
            input_data="Test message"
        )
        
        context = HandoffContext(conversation_id="test-123")
        
        # Execute handoff
        result = await engine.execute_handoff(request, context)
        
        assert result.success is True
        assert result.target_agent == "TargetAgent"
        mock_target.process_message.assert_called_once()


class TestControlFlowManager:
    """Test the control flow manager."""

    def test_control_flow_initialization(self):
        """Test ControlFlowManager initialization."""
        control_flow = ControlFlowManager()
        
        assert hasattr(control_flow, 'logger')
        assert hasattr(control_flow, '_conversations')
        assert control_flow._conversations == {}

    def test_control_flow_create_context(self):
        """Test creating handoff context."""
        control_flow = ControlFlowManager()
        
        context = control_flow.create_context("test-conversation")
        
        assert context.conversation_id == "test-conversation"
        assert context.call_stack == []
        assert context.handoff_count == 0
        assert context.shared_context == {}

    def test_control_flow_register_agents(self):
        """Test registering agents with control flow manager."""
        control_flow = ControlFlowManager()
        
        mock_agent1 = Mock()
        mock_agent1.name = "Agent1"
        mock_agent2 = Mock()
        mock_agent2.name = "Agent2"
        
        agents = {"Agent1": mock_agent1, "Agent2": mock_agent2}
        control_flow.register_agents(agents)
        
        # The method should complete without error
        assert True


class TestHandoffTypes:
    """Test handoff type classes."""

    def test_handoff_request_creation(self):
        """Test HandoffRequest creation."""
        request = HandoffRequest(
            target_agent="TargetAgent",
            input_data="Please handle this request",
            reason="User needs technical support"
        )
        
        assert request.target_agent == "TargetAgent"
        assert request.input_data == "Please handle this request"
        assert request.reason == "User needs technical support"
        assert request.expected_return == ControlReturn.RETURN_TO_CALLER

    def test_agent_response_creation(self):
        """Test AgentResponse creation."""
        response = AgentResponse(
            agent_name="TargetAgent",
            content="Request handled successfully",
            metadata={"processing_time": 1.5, "tokens_used": 150}
        )
        
        assert response.content == "Request handled successfully"
        assert response.agent_name == "TargetAgent"
        assert response.metadata["processing_time"] == 1.5
        assert response.metadata["tokens_used"] == 150

    def test_handoff_result_success(self):
        """Test HandoffResult for successful handoff."""
        response_data = {
            "message": "Success",
            "agent": "TargetAgent",
            "metadata": {}
        }
        
        result = HandoffResult(
            success=True,
            target_agent="TargetAgent",
            response=response_data,
            error=None
        )
        
        assert result.success is True
        assert result.target_agent == "TargetAgent"
        assert result.response == response_data
        assert result.error is None

    def test_handoff_result_failure(self):
        """Test HandoffResult for failed handoff."""
        result = HandoffResult(
            success=False,
            target_agent="NonExistentAgent",
            response=None,
            error="Target agent not found"
        )
        
        assert result.success is False
        assert result.target_agent == "NonExistentAgent"
        assert result.response is None
        assert result.error == "Target agent not found"

    def test_handoff_config_creation(self):
        """Test HandoffConfig creation."""
        target = HandoffTarget(agent_name="SpecialistAgent")
        
        config = HandoffConfig(
            mode=HandoffType.SWARM,
            strategy=HandoffStrategy.DIRECT,
            targets=[target]
        )
        
        assert config.mode == HandoffType.SWARM
        assert config.strategy == HandoffStrategy.DIRECT
        assert len(config.targets) == 1
        assert config.targets[0].agent_name == "SpecialistAgent"

    def test_handoff_context_creation(self):
        """Test HandoffContext creation."""
        context = HandoffContext(
            conversation_id="test-123",
            shared_context={"user_id": "user_456"}
        )
        
        assert context.conversation_id == "test-123"
        assert context.shared_context["user_id"] == "user_456"
        assert context.call_stack == []
        assert context.handoff_count == 0


class TestHandoffIntegration:
    """Test end-to-end handoff scenarios."""

    @pytest.mark.asyncio
    async def test_full_handoff_workflow(self):
        """Test a complete handoff workflow."""
        # Setup control flow manager and engine
        control_flow = ControlFlowManager()
        engine = HandoffEngine(control_flow)
        
        # Create mock agents
        mock_source = Mock()
        mock_source.name = "CustomerService"
        
        mock_target = Mock()
        mock_target.name = "TechnicalSupport"
        mock_target.process_message = AsyncMock(return_value="Technical issue resolved")
        
        agents = {"CustomerService": mock_source, "TechnicalSupport": mock_target}
        engine.register_agents(agents)
        
        # Create handoff request
        request = HandoffRequest(
            target_agent="TechnicalSupport",
            input_data="Customer has a technical issue with login",
            reason="Escalate to technical support"
        )
        
        # Create context
        context = HandoffContext(
            conversation_id="conv-789",
            shared_context={"customer_id": "cust_123", "priority": "high"}
        )
        
        # Execute handoff
        result = await engine.execute_handoff(request, context)
        
        # Verify results
        assert result.success is True
        assert result.target_agent == "TechnicalSupport"
        mock_target.process_message.assert_called_once()

    def test_handoff_config_with_multiple_targets(self):
        """Test handoff configuration with multiple target agents."""
        targets = [
            HandoffTarget(agent_name="TechnicalSupport", condition="priority == 'high'"),
            HandoffTarget(agent_name="GeneralSupport", condition="priority == 'normal'"),
        ]
        
        config = HandoffConfig(
            mode=HandoffType.CONDITIONAL,
            strategy=HandoffStrategy.ROUTE,
            targets=targets,
            routing_instructions="Route based on priority level"
        )
        
        assert len(config.targets) == 2
        assert config.targets[0].agent_name == "TechnicalSupport"
        assert config.targets[1].agent_name == "GeneralSupport"
        assert config.routing_instructions == "Route based on priority level"
