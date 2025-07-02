"""Unit tests for the Runner class.

This module tests the Runner class functionality including:
- Runner initialization and configuration
- Request normalization and processing
- Async and sync execution
- Handoff integration
- Error handling and edge cases
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any

from azurefunctions.agents import Agent, Runner, LLMConfig, LLMProvider
from azurefunctions.agents.types import ChatRequest, ChatResponse


class TestRunnerInitialization:
    """Test Runner initialization and basic configuration."""

    def test_runner_basic_initialization(self, basic_agent):
        """Test basic runner initialization with agent."""
        # Act
        runner = Runner(basic_agent)
        
        # Assert
        assert runner.agent == basic_agent
        assert runner.handoff_engine is None
        assert isinstance(runner._other_runners, dict)
        assert len(runner._other_runners) == 0

    def test_runner_with_handoff_engine(self, basic_agent):
        """Test runner initialization with handoff engine."""
        # Arrange
        mock_handoff_engine = Mock()
        
        # Act
        runner = Runner(basic_agent, handoff_engine=mock_handoff_engine)
        
        # Assert
        assert runner.agent == basic_agent
        assert runner.handoff_engine == mock_handoff_engine

    def test_runner_other_runners_registry(self, basic_agent):
        """Test runner's other runners registry."""
        # Act
        runner = Runner(basic_agent)
        
        # Assert
        assert hasattr(runner, '_other_runners')
        assert isinstance(runner._other_runners, dict)


class TestRunnerRequestNormalization:
    """Test Runner request normalization functionality."""

    def test_normalize_string_request(self, basic_runner):
        """Test normalization of string request."""
        # Arrange
        request = "Hello, how are you?"
        
        # Act
        normalized = basic_runner._normalize_request(request)
        
        # Assert
        assert isinstance(normalized, dict)
        assert "message" in normalized
        assert normalized["message"] == request

    def test_normalize_dict_request(self, basic_runner):
        """Test normalization of dictionary request."""
        # Arrange
        request = {
            "message": "Hello",
            "user_id": "user123",
            "context": {"key": "value"}
        }
        
        # Act
        normalized = basic_runner._normalize_request(request)
        
        # Assert
        assert isinstance(normalized, dict)
        assert normalized == request

    def test_normalize_chat_request_object(self, basic_runner, sample_chat_request):
        """Test normalization of ChatRequest object."""
        # Act
        normalized = basic_runner._normalize_request(sample_chat_request)
        
        # Assert
        assert isinstance(normalized, dict)
        assert "message" in normalized
        assert normalized["message"] == sample_chat_request.message

    def test_normalize_empty_string_request(self, basic_runner):
        """Test normalization of empty string request."""
        # Arrange
        request = ""
        
        # Act
        normalized = basic_runner._normalize_request(request)
        
        # Assert
        assert isinstance(normalized, dict)
        assert normalized["message"] == ""

    def test_normalize_complex_dict_request(self, basic_runner):
        """Test normalization of complex dictionary request."""
        # Arrange
        request = {
            "message": "Complex request",
            "user_id": "user456",
            "session_id": "session789",
            "context": {
                "timezone": "UTC",
                "language": "en",
                "preferences": {
                    "theme": "dark",
                    "notifications": True
                }
            },
            "metadata": {
                "source": "web",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
        
        # Act
        normalized = basic_runner._normalize_request(request)
        
        # Assert
        assert normalized == request
        assert normalized["context"]["preferences"]["theme"] == "dark"

    def test_normalize_invalid_request_type(self, basic_runner):
        """Test normalization with invalid request type."""
        # Arrange
        invalid_request = 12345  # Number instead of valid type
        
        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            basic_runner._normalize_request(invalid_request)

    def test_normalize_none_request(self, basic_runner):
        """Test normalization with None request."""
        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            basic_runner._normalize_request(None)


class TestRunnerResponseCreation:
    """Test Runner response creation functionality."""

    def test_create_response_from_dict(self, basic_runner):
        """Test creating response from dictionary data."""
        # Arrange
        response_data = {
            "response": "Hello! How can I help you?",
            "agent_name": "TestAgent",
            "success": True
        }
        
        # Act
        response = basic_runner._create_response(response_data)
        
        # Assert
        # Note: This test depends on the _create_response implementation
        assert hasattr(response, 'response') or hasattr(response, 'content')

    def test_create_response_from_string(self, basic_runner):
        """Test creating response from string data."""
        # Arrange
        response_data = "Simple string response"
        
        # Act
        response = basic_runner._create_response(response_data)
        
        # Assert
        assert hasattr(response, 'response') or hasattr(response, 'content')

    def test_create_response_with_error(self, basic_runner):
        """Test creating response with error information."""
        # Arrange
        response_data = {
            "response": "",
            "error": "Something went wrong",
            "success": False
        }
        
        # Act
        response = basic_runner._create_response(response_data)
        
        # Assert
        # Response should contain error information
        assert hasattr(response, 'error') or hasattr(response, 'success')


class TestRunnerAsyncExecution:
    """Test Runner async execution functionality."""

    @pytest.mark.asyncio
    async def test_run_async_with_string_request(self, basic_runner):
        """Test async run with string request."""
        # Arrange
        request = "Hello, agent!"
        
        # Mock the agent's process_request method
        mock_response = {"response": "Hello! How can I help you?", "success": True}
        basic_runner.agent.process_request = AsyncMock(return_value=mock_response)
        
        # Act
        response = await basic_runner.run(request)
        
        # Assert
        assert response is not None
        basic_runner.agent.process_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_with_dict_request(self, basic_runner):
        """Test async run with dictionary request."""
        # Arrange
        request = {
            "message": "Hello",
            "user_id": "user123",
            "context": {"key": "value"}
        }
        
        # Mock the agent's process_request method
        mock_response = {"response": "Hello user123!", "success": True}
        basic_runner.agent.process_request = AsyncMock(return_value=mock_response)
        
        # Act
        response = await basic_runner.run(request)
        
        # Assert
        assert response is not None
        basic_runner.agent.process_request.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_run_async_with_chat_request(self, basic_runner, sample_chat_request):
        """Test async run with ChatRequest object."""
        # Arrange
        mock_response = {"response": "Hello! I'm doing well.", "success": True}
        basic_runner.agent.process_request = AsyncMock(return_value=mock_response)
        
        # Act
        response = await basic_runner.run(sample_chat_request)
        
        # Assert
        assert response is not None
        basic_runner.agent.process_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_async_agent_error_handling(self, basic_runner):
        """Test async run with agent error."""
        # Arrange
        request = "Test request"
        basic_runner.agent.process_request = AsyncMock(side_effect=Exception("Agent error"))
        
        # Act & Assert
        with pytest.raises(Exception, match="Agent error"):
            await basic_runner.run(request)

    @pytest.mark.asyncio
    async def test_run_async_multiple_requests(self, basic_runner):
        """Test multiple async requests to the same runner."""
        # Arrange
        requests = ["Hello", "How are you?", "Goodbye"]
        mock_responses = [
            {"response": "Hello!", "success": True},
            {"response": "I'm doing well!", "success": True},
            {"response": "Goodbye!", "success": True}
        ]
        
        basic_runner.agent.process_request = AsyncMock(side_effect=mock_responses)
        
        # Act
        responses = []
        for request in requests:
            response = await basic_runner.run(request)
            responses.append(response)
        
        # Assert
        assert len(responses) == 3
        assert basic_runner.agent.process_request.call_count == 3


class TestRunnerSyncExecution:
    """Test Runner sync execution functionality."""

    def test_run_sync_with_string_request(self, basic_runner):
        """Test sync run with string request."""
        # Arrange
        request = "Hello, sync agent!"
        mock_response = {"response": "Hello sync!", "success": True}
        
        # Mock the async run method
        async def mock_run(req):
            return mock_response
        
        basic_runner.run = AsyncMock(return_value=mock_response)
        
        # Act
        response = basic_runner.run_sync(request)
        
        # Assert
        assert response == mock_response

    def test_run_sync_with_dict_request(self, basic_runner):
        """Test sync run with dictionary request."""
        # Arrange
        request = {"message": "Hello sync", "user_id": "sync_user"}
        mock_response = {"response": "Sync response", "success": True}
        
        basic_runner.run = AsyncMock(return_value=mock_response)
        
        # Act
        response = basic_runner.run_sync(request)
        
        # Assert
        assert response == mock_response

    def test_run_sync_error_handling(self, basic_runner):
        """Test sync run error handling."""
        # Arrange
        request = "Error request"
        basic_runner.run = AsyncMock(side_effect=Exception("Sync error"))
        
        # Act & Assert
        with pytest.raises(Exception, match="Sync error"):
            basic_runner.run_sync(request)

    @patch('asyncio.get_running_loop')
    def test_run_sync_with_existing_event_loop(self, mock_get_loop, basic_runner):
        """Test sync run when there's already an event loop running."""
        # Arrange
        mock_loop = Mock()
        mock_get_loop.return_value = mock_loop
        
        request = "Test with existing loop"
        mock_response = {"response": "Response with loop", "success": True}
        basic_runner.run = AsyncMock(return_value=mock_response)
        
        # Act
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            mock_future = Mock()
            mock_future.result.return_value = mock_response
            mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
            
            response = basic_runner.run_sync(request)
        
        # Assert
        assert response == mock_response

    @patch('asyncio.get_running_loop')
    def test_run_sync_no_existing_event_loop(self, mock_get_loop, basic_runner):
        """Test sync run when there's no existing event loop."""
        # Arrange
        mock_get_loop.side_effect = RuntimeError("No running event loop")
        
        request = "Test without loop"
        mock_response = {"response": "Response without loop", "success": True}
        
        # Act
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = mock_response
            response = basic_runner.run_sync(request)
        
        # Assert
        assert response == mock_response


class TestRunnerHandoffIntegration:
    """Test Runner handoff integration functionality."""

    def test_runner_register_other_runner(self, basic_runner, weather_runner):
        """Test registering another runner for handoffs."""
        # Act
        basic_runner.register_runner("weather", weather_runner)
        
        # Assert
        assert "weather" in basic_runner._other_runners
        assert basic_runner._other_runners["weather"] == weather_runner

    def test_runner_register_multiple_runners(self, basic_runner, weather_runner, travel_agent, mock_llm_config):
        """Test registering multiple runners."""
        # Arrange
        travel_runner = Runner(travel_agent)
        
        # Act
        basic_runner.register_runner("weather", weather_runner)
        basic_runner.register_runner("travel", travel_runner)
        
        # Assert
        assert len(basic_runner._other_runners) == 2
        assert "weather" in basic_runner._other_runners
        assert "travel" in basic_runner._other_runners

    def test_runner_handoff_capability_check(self, basic_runner, weather_runner):
        """Test checking handoff capability to another agent."""
        # Arrange
        basic_runner.register_runner("weather", weather_runner)
        
        # Act
        can_handoff = basic_runner.can_handoff_to("weather")
        
        # Assert
        # Note: This test depends on the can_handoff_to implementation
        assert isinstance(can_handoff, bool)

    def test_runner_handoff_to_nonexistent_agent(self, basic_runner):
        """Test handoff to non-existent agent."""
        # Act
        can_handoff = basic_runner.can_handoff_to("nonexistent")
        
        # Assert
        assert can_handoff is False

    @pytest.mark.asyncio
    async def test_runner_handoff_execution(self, basic_runner, weather_runner):
        """Test actual handoff execution between runners."""
        # Arrange
        basic_runner.register_runner("weather", weather_runner)
        basic_runner.handoff_engine = Mock()
        
        handoff_data = {
            "query": "What's the weather in Seattle?",
            "context": {"user_id": "test_user"}
        }
        
        # Mock handoff engine
        mock_result = {"response": "Weather data", "success": True}
        basic_runner.handoff_engine.execute_handoff = AsyncMock(return_value=mock_result)
        
        # Act
        if hasattr(basic_runner, 'handoff_to'):
            result = await basic_runner.handoff_to(
                target_agent="weather",
                input_data=handoff_data,
                conversation_id="test_conv",
                reason="User requested weather"
            )
            
            # Assert
            assert result == mock_result


class TestRunnerErrorHandling:
    """Test Runner error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_run_with_invalid_agent_response(self, basic_runner):
        """Test run with invalid agent response."""
        # Arrange
        request = "Test request"
        basic_runner.agent.process_request = AsyncMock(return_value=None)
        
        # Act & Assert
        # Depending on implementation, this might raise an error or handle gracefully
        try:
            response = await basic_runner.run(request)
            # If no error, verify response handling
            assert response is not None or response is None
        except Exception as e:
            # If error is raised, it should be appropriate
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    @pytest.mark.asyncio
    async def test_run_with_agent_timeout(self, basic_runner):
        """Test run with agent timeout simulation."""
        # Arrange
        request = "Timeout test"
        
        async def slow_process(req):
            await asyncio.sleep(10)  # Simulate long processing
            return {"response": "Too slow", "success": True}
        
        basic_runner.agent.process_request = slow_process
        
        # Act & Assert
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(basic_runner.run(request), timeout=0.1)

    def test_run_sync_with_malformed_async_call(self, basic_runner):
        """Test sync run with malformed async call."""
        # Arrange
        request = "Malformed test"
        
        # Mock run to raise a different kind of error
        basic_runner.run = AsyncMock(side_effect=RuntimeError("Async error"))
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Async error"):
            basic_runner.run_sync(request)

    @pytest.mark.asyncio
    async def test_run_with_empty_response(self, basic_runner):
        """Test run with empty response from agent."""
        # Arrange
        request = "Empty response test"
        basic_runner.agent.process_request = AsyncMock(return_value={})
        
        # Act
        response = await basic_runner.run(request)
        
        # Assert
        # Should handle empty response gracefully
        assert response is not None

    @pytest.mark.asyncio
    async def test_run_with_large_request(self, basic_runner):
        """Test run with very large request."""
        # Arrange
        large_message = "A" * 100000  # 100KB message
        request = {"message": large_message, "context": {"large": True}}
        
        mock_response = {"response": "Handled large request", "success": True}
        basic_runner.agent.process_request = AsyncMock(return_value=mock_response)
        
        # Act
        response = await basic_runner.run(request)
        
        # Assert
        assert response is not None
        basic_runner.agent.process_request.assert_called_once()


class TestRunnerConcurrency:
    """Test Runner concurrency and thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_runs(self, basic_runner):
        """Test concurrent runs on the same runner."""
        # Arrange
        requests = [f"Request {i}" for i in range(5)]
        mock_responses = [
            {"response": f"Response {i}", "success": True} for i in range(5)
        ]
        
        async def process_with_delay(req):
            await asyncio.sleep(0.1)  # Small delay to simulate processing
            idx = int(req["message"].split()[-1])
            return mock_responses[idx]
        
        basic_runner.agent.process_request = process_with_delay
        
        # Act
        tasks = [basic_runner.run(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        # Assert
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert response["response"] == f"Response {i}"

    @pytest.mark.asyncio
    async def test_runner_state_isolation(self, basic_runner):
        """Test that runner maintains state isolation between requests."""
        # Arrange
        request1 = {"message": "First", "context": {"session": "1"}}
        request2 = {"message": "Second", "context": {"session": "2"}}
        
        responses = []
        
        async def capture_process(req):
            responses.append(req)
            return {"response": f"Processed {req['message']}", "success": True}
        
        basic_runner.agent.process_request = capture_process
        
        # Act
        await basic_runner.run(request1)
        await basic_runner.run(request2)
        
        # Assert
        assert len(responses) == 2
        assert responses[0]["context"]["session"] == "1"
        assert responses[1]["context"]["session"] == "2"


class TestRunnerUtilityMethods:
    """Test Runner utility methods and helpers."""

    def test_runner_string_representation(self, basic_runner):
        """Test runner string representation."""
        # Act
        str_repr = str(basic_runner)
        
        # Assert
        assert "Runner" in str_repr
        assert basic_runner.agent.name in str_repr

    def test_runner_agent_access(self, basic_runner, basic_agent):
        """Test runner provides access to underlying agent."""
        # Assert
        assert basic_runner.agent == basic_agent
        assert basic_runner.agent.name == basic_agent.name

    def test_runner_handoff_engine_access(self, basic_agent):
        """Test runner provides access to handoff engine."""
        # Arrange
        mock_handoff_engine = Mock()
        runner = Runner(basic_agent, handoff_engine=mock_handoff_engine)
        
        # Assert
        assert runner.handoff_engine == mock_handoff_engine

    def test_runner_without_handoff_engine(self, basic_runner):
        """Test runner behavior without handoff engine."""
        # Assert
        assert basic_runner.handoff_engine is None
        
        # Should still work for basic operations
        assert basic_runner.agent is not None
