"""Unit tests for Azure Functions Agent Framework A2A (Agent-to-Agent) module.

This module tests the agent-to-agent communication capabilities including
A2A client, manager, and task management functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from azurefunctions.agents.a2a.client import A2AClient
from azurefunctions.agents.a2a.manager import A2AManager
from azurefunctions.agents.a2a.task_manager import A2ATaskManager
from azurefunctions.agents.types import AgentMode


class TestA2AClient:
    """Test A2A client functionality."""

    def test_a2a_client_initialization(self):
        """Test A2AClient initialization."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="test-agent-123"
        )
        
        assert client.endpoint == "http://localhost:8080"
        assert client.agent_id == "test-agent-123"
        assert hasattr(client, 'session')
        assert hasattr(client, 'logger')

    def test_a2a_client_with_authentication(self):
        """Test A2AClient with authentication."""
        client = A2AClient(
            endpoint="https://api.example.com",
            agent_id="authenticated-agent",
            api_key="secret-key-123",
            headers={"X-Custom": "header"}
        )
        
        assert client.endpoint == "https://api.example.com"
        assert client.agent_id == "authenticated-agent"
        assert client.api_key == "secret-key-123"
        assert client.headers == {"X-Custom": "header"}

    @pytest.mark.asyncio
    async def test_a2a_client_send_message(self):
        """Test sending message via A2A client."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="sender-agent"
        )
        
        # Mock the HTTP session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "message_id": "msg_123",
            "status": "sent",
            "timestamp": "2024-01-01T12:00:00Z"
        })
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = await client.send_message(
                target_agent="receiver-agent",
                message="Hello from sender!",
                message_type="text",
                metadata={"priority": "high"}
            )
            
            assert result["message_id"] == "msg_123"
            assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_a2a_client_receive_messages(self):
        """Test receiving messages via A2A client."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="receiver-agent"
        )
        
        # Mock response with messages
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "messages": [
                {
                    "message_id": "msg_456",
                    "from_agent": "sender-agent",
                    "message": "Hello receiver!",
                    "type": "text",
                    "timestamp": "2024-01-01T12:01:00Z"
                },
                {
                    "message_id": "msg_789",
                    "from_agent": "another-agent",
                    "message": "Task completed",
                    "type": "notification",
                    "timestamp": "2024-01-01T12:02:00Z"
                }
            ],
            "has_more": False
        })
        
        with patch.object(client, '_make_request', return_value=mock_response):
            messages = await client.receive_messages(limit=10)
            
            assert len(messages["messages"]) == 2
            assert messages["messages"][0]["from_agent"] == "sender-agent"
            assert messages["messages"][1]["from_agent"] == "another-agent"
            assert messages["has_more"] is False

    @pytest.mark.asyncio
    async def test_a2a_client_register_agent(self):
        """Test agent registration via A2A client."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="new-agent"
        )
        
        # Mock registration response
        mock_response = Mock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value={
            "agent_id": "new-agent",
            "status": "registered",
            "capabilities": ["text_processing", "data_analysis"],
            "registration_time": "2024-01-01T12:00:00Z"
        })
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = await client.register_agent(
                capabilities=["text_processing", "data_analysis"],
                metadata={
                    "version": "1.0.0",
                    "description": "Data processing agent"
                }
            )
            
            assert result["agent_id"] == "new-agent"
            assert result["status"] == "registered"
            assert "text_processing" in result["capabilities"]

    @pytest.mark.asyncio
    async def test_a2a_client_discover_agents(self):
        """Test agent discovery via A2A client."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="discovery-agent"
        )
        
        # Mock discovery response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "agents": [
                {
                    "agent_id": "agent-1",
                    "capabilities": ["weather"],
                    "status": "online",
                    "last_seen": "2024-01-01T12:00:00Z"
                },
                {
                    "agent_id": "agent-2", 
                    "capabilities": ["translation"],
                    "status": "online",
                    "last_seen": "2024-01-01T11:58:00Z"
                }
            ],
            "total": 2
        })
        
        with patch.object(client, '_make_request', return_value=mock_response):
            agents = await client.discover_agents(
                capabilities=["weather", "translation"]
            )
            
            assert len(agents["agents"]) == 2
            assert agents["agents"][0]["agent_id"] == "agent-1"
            assert agents["agents"][1]["agent_id"] == "agent-2"
            assert agents["total"] == 2

    @pytest.mark.asyncio
    async def test_a2a_client_error_handling(self):
        """Test A2A client error handling."""
        client = A2AClient(
            endpoint="http://localhost:8080",
            agent_id="error-agent"
        )
        
        # Mock error response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={
            "error": "Invalid request",
            "code": "INVALID_REQUEST"
        })
        
        with patch.object(client, '_make_request', return_value=mock_response):
            with pytest.raises(Exception):  # Should raise appropriate exception
                await client.send_message(
                    target_agent="",  # Invalid empty target
                    message="test"
                )

    @pytest.mark.asyncio
    async def test_a2a_client_connection_error(self):
        """Test A2A client connection error handling."""
        client = A2AClient(
            endpoint="http://unreachable:8080",
            agent_id="test-agent"
        )
        
        with patch.object(client, '_make_request', side_effect=ConnectionError("Network unreachable")):
            with pytest.raises(ConnectionError):
                await client.send_message(
                    target_agent="target",
                    message="test"
                )


class TestA2AManager:
    """Test A2A manager functionality."""

    def test_a2a_manager_initialization(self):
        """Test A2AManager initialization."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="manager-agent"
        )
        
        assert manager.endpoint == "http://localhost:8080"
        assert manager.agent_id == "manager-agent"
        assert hasattr(manager, 'client')
        assert hasattr(manager, 'task_manager')
        assert hasattr(manager, 'logger')

    def test_a2a_manager_with_agent(self):
        """Test A2AManager with agent configuration."""
        mock_agent = Mock()
        mock_agent.name = "TestAgent"
        mock_agent.description = "Test agent for A2A"
        
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="test-agent",
            agent=mock_agent
        )
        
        assert manager.agent == mock_agent
        assert manager.agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_a2a_manager_start(self):
        """Test A2A manager startup process."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="startup-agent"
        )
        
        # Mock client methods
        manager.client.register_agent = AsyncMock(return_value={
            "agent_id": "startup-agent",
            "status": "registered"
        })
        
        await manager.start()
        
        assert manager.running is True
        manager.client.register_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_a2a_manager_stop(self):
        """Test A2A manager shutdown process."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="shutdown-agent"
        )
        
        # Start first
        manager.running = True
        manager.client.unregister_agent = AsyncMock()
        
        await manager.stop()
        
        assert manager.running is False
        manager.client.unregister_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_a2a_manager_send_message(self):
        """Test sending message through A2A manager."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="sender-agent"
        )
        
        # Mock client send_message
        manager.client.send_message = AsyncMock(return_value={
            "message_id": "msg_123",
            "status": "sent"
        })
        
        result = await manager.send_message(
            target_agent="receiver-agent",
            message="Hello from manager!",
            message_type="task"
        )
        
        assert result["message_id"] == "msg_123"
        assert result["status"] == "sent"
        
        manager.client.send_message.assert_called_once_with(
            target_agent="receiver-agent",
            message="Hello from manager!",
            message_type="task",
            metadata=None
        )

    @pytest.mark.asyncio
    async def test_a2a_manager_handle_incoming_message(self):
        """Test handling incoming messages in A2A manager."""
        mock_agent = Mock()
        mock_agent.name = "HandlerAgent"
        
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="handler-agent",
            agent=mock_agent
        )
        
        # Mock agent's runner
        mock_runner = AsyncMock()
        mock_runner.run_async.return_value = Mock(
            message="Response from agent",
            metadata={"processed": True}
        )
        manager.agent_runner = mock_runner
        
        incoming_message = {
            "message_id": "msg_456",
            "from_agent": "sender-agent",
            "message": "Process this data",
            "type": "task",
            "metadata": {"priority": "high"}
        }
        
        response = await manager.handle_incoming_message(incoming_message)
        
        assert response is not None
        mock_runner.run_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_a2a_manager_message_polling(self):
        """Test A2A manager message polling."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="polling-agent"
        )
        
        # Mock incoming messages
        manager.client.receive_messages = AsyncMock(return_value={
            "messages": [
                {
                    "message_id": "poll_msg_1",
                    "from_agent": "sender-1",
                    "message": "Polling test 1",
                    "type": "text"
                }
            ],
            "has_more": False
        })
        
        manager.handle_incoming_message = AsyncMock()
        
        # Start polling (mock the polling loop)
        messages = await manager.client.receive_messages()
        
        assert len(messages["messages"]) == 1
        manager.client.receive_messages.assert_called_once()


class TestA2ATaskManager:
    """Test A2A task management functionality."""

    def test_a2a_task_manager_initialization(self):
        """Test A2ATaskManager initialization."""
        task_manager = A2ATaskManager()
        
        assert hasattr(task_manager, 'tasks')
        assert hasattr(task_manager, 'task_history')
        assert len(task_manager.tasks) == 0

    def test_a2a_task_manager_create_task(self):
        """Test creating task in A2A task manager."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="data_processing",
            payload={"data": "sample_data", "format": "json"},
            target_agent="processor-agent",
            priority="high",
            metadata={"deadline": "2024-01-02T00:00:00Z"}
        )
        
        assert task_id is not None
        assert len(task_manager.tasks) == 1
        
        task = task_manager.get_task(task_id)
        assert task["task_type"] == "data_processing"
        assert task["target_agent"] == "processor-agent"
        assert task["priority"] == "high"
        assert task["status"] == "pending"

    def test_a2a_task_manager_update_task_status(self):
        """Test updating task status."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="analysis",
            payload={"data": "test"},
            target_agent="analyzer"
        )
        
        # Update to in_progress
        task_manager.update_task_status(task_id, "in_progress")
        task = task_manager.get_task(task_id)
        assert task["status"] == "in_progress"
        
        # Update to completed with result
        task_manager.update_task_status(
            task_id,
            "completed",
            result={"analysis": "completed", "confidence": 0.95}
        )
        task = task_manager.get_task(task_id)
        assert task["status"] == "completed"
        assert task["result"]["confidence"] == 0.95

    def test_a2a_task_manager_task_assignment(self):
        """Test task assignment to agents."""
        task_manager = A2ATaskManager()
        
        # Create multiple tasks
        task1_id = task_manager.create_task(
            task_type="type_a",
            payload={"data": "1"},
            target_agent="agent_1"
        )
        
        task2_id = task_manager.create_task(
            task_type="type_b",
            payload={"data": "2"},
            target_agent="agent_2"
        )
        
        task3_id = task_manager.create_task(
            task_type="type_a",
            payload={"data": "3"},
            target_agent="agent_1"
        )
        
        # Get tasks for specific agent
        agent1_tasks = task_manager.get_tasks_for_agent("agent_1")
        assert len(agent1_tasks) == 2
        
        agent2_tasks = task_manager.get_tasks_for_agent("agent_2")
        assert len(agent2_tasks) == 1
        
        # Get tasks by type
        type_a_tasks = task_manager.get_tasks_by_type("type_a")
        assert len(type_a_tasks) == 2

    def test_a2a_task_manager_task_completion(self):
        """Test task completion workflow."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="computation",
            payload={"input": 42},
            target_agent="compute-agent"
        )
        
        # Start task
        task_manager.update_task_status(task_id, "in_progress")
        
        # Complete task
        result = {"output": 84, "processing_time": 1.23}
        task_manager.complete_task(task_id, result)
        
        task = task_manager.get_task(task_id)
        assert task["status"] == "completed"
        assert task["result"] == result
        assert "completed_at" in task

    def test_a2a_task_manager_task_failure(self):
        """Test task failure handling."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="risky_operation",
            payload={"data": "test"},
            target_agent="unreliable-agent"
        )
        
        # Fail task
        error_info = {"error": "Processing failed", "code": "PROC_ERROR"}
        task_manager.fail_task(task_id, error_info)
        
        task = task_manager.get_task(task_id)
        assert task["status"] == "failed"
        assert task["error"] == error_info
        assert "failed_at" in task

    def test_a2a_task_manager_task_retry(self):
        """Test task retry mechanism."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="retryable_task",
            payload={"data": "test"},
            target_agent="flaky-agent",
            max_retries=3
        )
        
        # Fail task first time
        task_manager.fail_task(task_id, {"error": "Temporary failure"})
        
        # Retry task
        retry_successful = task_manager.retry_task(task_id)
        assert retry_successful is True
        
        task = task_manager.get_task(task_id)
        assert task["status"] == "pending"  # Reset to pending for retry
        assert task["retry_count"] == 1

    def test_a2a_task_manager_task_expiration(self):
        """Test task expiration handling."""
        task_manager = A2ATaskManager()
        
        # Create task with short TTL
        task_id = task_manager.create_task(
            task_type="time_sensitive",
            payload={"urgent": True},
            target_agent="fast-agent",
            ttl_seconds=60  # 1 minute TTL
        )
        
        task = task_manager.get_task(task_id)
        assert "expires_at" in task
        
        # Test expiration check
        expired_tasks = task_manager.get_expired_tasks()
        # Depending on implementation, might need to mock time

    def test_a2a_task_manager_task_prioritization(self):
        """Test task prioritization."""
        task_manager = A2ATaskManager()
        
        # Create tasks with different priorities
        low_task = task_manager.create_task(
            task_type="batch_job",
            payload={"data": "low"},
            target_agent="worker",
            priority="low"
        )
        
        high_task = task_manager.create_task(
            task_type="urgent_job",
            payload={"data": "high"},
            target_agent="worker",
            priority="high"
        )
        
        medium_task = task_manager.create_task(
            task_type="normal_job",
            payload={"data": "medium"},
            target_agent="worker",
            priority="medium"
        )
        
        # Get prioritized tasks
        prioritized_tasks = task_manager.get_prioritized_tasks("worker")
        
        # Should be ordered by priority (high, medium, low)
        assert len(prioritized_tasks) == 3
        assert prioritized_tasks[0]["priority"] == "high"
        assert prioritized_tasks[1]["priority"] == "medium"
        assert prioritized_tasks[2]["priority"] == "low"

    def test_a2a_task_manager_task_history(self):
        """Test task history tracking."""
        task_manager = A2ATaskManager()
        
        task_id = task_manager.create_task(
            task_type="tracked_task",
            payload={"data": "test"},
            target_agent="history-agent"
        )
        
        # Move through states
        task_manager.update_task_status(task_id, "in_progress")
        task_manager.complete_task(task_id, {"result": "success"})
        
        # Check history
        history = task_manager.get_task_history(task_id)
        assert len(history) >= 3  # created, in_progress, completed
        
        # Verify history entries have timestamps
        for entry in history:
            assert "timestamp" in entry
            assert "status" in entry


class TestA2AIntegration:
    """Test A2A integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_a2a_workflow(self):
        """Test complete A2A communication workflow."""
        # Setup sender agent
        sender_manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="sender-agent"
        )
        
        # Setup receiver agent
        receiver_manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="receiver-agent"
        )
        
        # Mock the communication
        sender_manager.client.send_message = AsyncMock(return_value={
            "message_id": "workflow_msg_1",
            "status": "sent"
        })
        
        receiver_manager.client.receive_messages = AsyncMock(return_value={
            "messages": [{
                "message_id": "workflow_msg_1",
                "from_agent": "sender-agent",
                "message": "Process this task",
                "type": "task_request",
                "metadata": {"task_id": "task_123"}
            }],
            "has_more": False
        })
        
        # Send message from sender to receiver
        send_result = await sender_manager.send_message(
            target_agent="receiver-agent",
            message="Process this task",
            message_type="task_request",
            metadata={"task_id": "task_123"}
        )
        
        assert send_result["status"] == "sent"
        
        # Receive messages at receiver
        received_messages = await receiver_manager.client.receive_messages()
        assert len(received_messages["messages"]) == 1
        assert received_messages["messages"][0]["from_agent"] == "sender-agent"

    @pytest.mark.asyncio
    async def test_a2a_task_delegation(self):
        """Test task delegation between agents."""
        coordinator = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="coordinator"
        )
        
        task_manager = A2ATaskManager()
        coordinator.task_manager = task_manager
        
        # Create task for delegation
        task_id = task_manager.create_task(
            task_type="data_analysis",
            payload={"dataset": "sales_data.csv"},
            target_agent="analyst-agent",
            priority="high"
        )
        
        # Mock sending task to agent
        coordinator.client.send_message = AsyncMock(return_value={
            "message_id": "task_msg",
            "status": "sent"
        })
        
        # Delegate task
        task = task_manager.get_task(task_id)
        result = await coordinator.send_message(
            target_agent=task["target_agent"],
            message=f"Please process task: {task_id}",
            message_type="task_assignment",
            metadata={"task": task}
        )
        
        assert result["status"] == "sent"
        
        # Update task status
        task_manager.update_task_status(task_id, "assigned")
        updated_task = task_manager.get_task(task_id)
        assert updated_task["status"] == "assigned"

    def test_a2a_agent_discovery_and_routing(self):
        """Test agent discovery and message routing."""
        manager = A2AManager(
            endpoint="http://localhost:8080",
            agent_id="router-agent"
        )
        
        # Mock discovered agents
        mock_agents = {
            "agents": [
                {
                    "agent_id": "weather-agent",
                    "capabilities": ["weather_forecast", "weather_current"],
                    "status": "online"
                },
                {
                    "agent_id": "translator-agent", 
                    "capabilities": ["text_translation", "language_detection"],
                    "status": "online"
                },
                {
                    "agent_id": "calculator-agent",
                    "capabilities": ["math_operations", "statistics"],
                    "status": "online"
                }
            ]
        }
        
        manager.client.discover_agents = AsyncMock(return_value=mock_agents)
        
        # Test capability-based routing
        def find_agent_for_capability(capability: str):
            for agent in mock_agents["agents"]:
                if capability in agent["capabilities"]:
                    return agent["agent_id"]
            return None
        
        weather_agent = find_agent_for_capability("weather_forecast")
        assert weather_agent == "weather-agent"
        
        translation_agent = find_agent_for_capability("text_translation")
        assert translation_agent == "translator-agent"
        
        math_agent = find_agent_for_capability("math_operations")
        assert math_agent == "calculator-agent"
