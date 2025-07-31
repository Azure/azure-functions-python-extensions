"""
Unit tests for STDIO adapter functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from azurefunctions.extensions.mcp_server.core.stdio_adapter import MCPStdioAdapter
from azurefunctions.extensions.mcp_server.models.enums import MCPServerStatus


class TestMCPStdioAdapter:
    """Test MCPStdioAdapter class."""
    
    async def test_initialization(self, sample_mcp_config):
        """Test adapter initialization."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        assert adapter.config == sample_mcp_config
        assert not adapter.is_connected
        assert adapter.status == MCPServerStatus.STOPPED
        assert adapter._read_buffer == b''
        assert adapter._messages_sent == 0
        assert adapter._messages_received == 0
    
    async def test_connect_success(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test successful connection to MCP server."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            success = await adapter.connect()
            
            assert success
            assert adapter.is_connected
            assert adapter.status == MCPServerStatus.RUNNING
    
    async def test_connect_failure(self, sample_mcp_config):
        """Test connection failure."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        # Mock process manager start to fail
        adapter.process_manager.start = AsyncMock(return_value=False)
        
        success = await adapter.connect()
        
        assert not success
        assert not adapter.is_connected
    
    async def test_disconnect(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test disconnection from MCP server."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            # Connect first
            await adapter.connect()
            assert adapter.is_connected
            
            # Then disconnect
            success = await adapter.disconnect()
            
            assert success
            assert not adapter.is_connected
    
    async def test_send_message_not_connected(self, sample_mcp_config):
        """Test sending message when not connected."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
        success = await adapter.send_message(message)
        
        assert not success
    
    async def test_send_message_success(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test successful message sending."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
            success = await adapter.send_message(message)
            
            assert success
            assert adapter._messages_sent == 1
            assert adapter._bytes_sent > 0
    
    async def test_content_length_framing(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test line-delimited JSON framing of messages."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
            
            # Mock the send_input to capture what's sent
            sent_data = []
            async def mock_send_input(data):
                sent_data.append(data)
                return True
            
            adapter.process_manager.send_input = mock_send_input
            
            await adapter.send_message(message)
            
            # Verify line-delimited JSON framing
            assert len(sent_data) == 1
            frame = sent_data[0]
            
            # Should be JSON message followed by newline
            assert frame.endswith(b'\n')
            
            # Parse message (remove newline)
            message_part = frame[:-1]
            parsed_message = json.loads(message_part.decode('utf-8'))
            assert parsed_message == message
    
    async def test_process_buffer_complete_message(self, sample_mcp_config):
        """Test processing complete line-delimited JSON message from buffer."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        # Create a complete line-delimited JSON message
        message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
        message_json = json.dumps(message)
        frame = message_json.encode('utf-8') + b'\n'
        
        # Set up message handler
        received_messages = []
        async def message_handler(msg):
            received_messages.append(msg)
        
        adapter.message_handler = message_handler
        adapter._read_buffer = frame
        
        # Process the buffer
        await adapter._process_buffer()
        
        # Verify message was processed
        assert len(received_messages) == 1
        assert received_messages[0] == message
        assert adapter._messages_received == 1
        assert adapter._read_buffer == b''  # Buffer should be empty
    
    async def test_process_buffer_incomplete_message(self, sample_mcp_config):
        """Test processing incomplete line-delimited JSON message from buffer."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        # Create an incomplete message (JSON without newline)
        message = {"jsonrpc": "2.0", "method": "test", "id": "1"}
        message_json = json.dumps(message)
        # No newline - incomplete message
        frame = message_json.encode('utf-8')
        
        adapter._read_buffer = frame
        
        # Process the buffer
        await adapter._process_buffer()
        
        # Message should not be processed yet
        assert adapter._messages_received == 0
        assert adapter._read_buffer == frame  # Buffer should remain unchanged
    
    async def test_process_buffer_multiple_messages(self, sample_mcp_config):
        """Test processing multiple line-delimited JSON messages from buffer."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        # Create two complete message lines
        messages = [
            {"jsonrpc": "2.0", "method": "test1", "id": "1"},
            {"jsonrpc": "2.0", "method": "test2", "id": "2"}
        ]
        
        frames = b''
        for message in messages:
            message_json = json.dumps(message)
            frame = message_json.encode('utf-8') + b'\n'
            frames += frame
        
        # Set up message handler
        received_messages = []
        async def message_handler(msg):
            received_messages.append(msg)
        
        adapter.message_handler = message_handler
        adapter._read_buffer = frames
        
        # Process the buffer
        await adapter._process_buffer()
        
        # Verify both messages were processed
        assert len(received_messages) == 2
        assert received_messages[0] == messages[0]
        assert received_messages[1] == messages[1]
        assert adapter._messages_received == 2
        assert adapter._read_buffer == b''  # Buffer should be empty
    
    async def test_send_request(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test sending JSON-RPC request."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            # Mock send_message to verify the request format
            sent_messages = []
            async def mock_send_message(message):
                sent_messages.append(message)
                return True
            
            adapter.send_message = mock_send_message
            
            success = await adapter.send_request(
                "test_method", 
                {"param": "value"}, 
                "request-123"
            )
            
            assert success
            assert len(sent_messages) == 1
            
            message = sent_messages[0]
            assert message["jsonrpc"] == "2.0"
            assert message["method"] == "test_method"
            assert message["params"] == {"param": "value"}
            assert message["id"] == "request-123"
    
    async def test_send_response(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test sending JSON-RPC response."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            # Mock send_message to verify the response format
            sent_messages = []
            async def mock_send_message(message):
                sent_messages.append(message)
                return True
            
            adapter.send_message = mock_send_message
            
            success = await adapter.send_response(
                "request-123",
                result={"data": "test"}
            )
            
            assert success
            assert len(sent_messages) == 1
            
            message = sent_messages[0]
            assert message["jsonrpc"] == "2.0"
            assert message["id"] == "request-123"
            assert message["result"] == {"data": "test"}
            assert "error" not in message
    
    async def test_send_error_response(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test sending JSON-RPC error response."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            # Mock send_message to verify the error response format
            sent_messages = []
            async def mock_send_message(message):
                sent_messages.append(message)
                return True
            
            adapter.send_message = mock_send_message
            
            error = {"code": -32600, "message": "Invalid Request"}
            success = await adapter.send_response("request-123", error=error)
            
            assert success
            assert len(sent_messages) == 1
            
            message = sent_messages[0]
            assert message["jsonrpc"] == "2.0"
            assert message["id"] == "request-123"
            assert message["error"] == error
            assert "result" not in message
    
    async def test_send_notification(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test sending JSON-RPC notification."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await adapter.connect()
            
            # Mock send_message to verify the notification format
            sent_messages = []
            async def mock_send_message(message):
                sent_messages.append(message)
                return True
            
            adapter.send_message = mock_send_message
            
            success = await adapter.send_notification(
                "notification_method",
                {"param": "value"}
            )
            
            assert success
            assert len(sent_messages) == 1
            
            message = sent_messages[0]
            assert message["jsonrpc"] == "2.0"
            assert message["method"] == "notification_method"
            assert message["params"] == {"param": "value"}
            assert "id" not in message  # Notifications don't have IDs
    
    async def test_stats(self, sample_mcp_config):
        """Test statistics collection."""
        adapter = MCPStdioAdapter(sample_mcp_config)
        
        # Initially empty stats
        stats = adapter.stats
        assert stats["messages_sent"] == 0
        assert stats["messages_received"] == 0
        assert stats["bytes_sent"] == 0
        assert stats["bytes_received"] == 0
        assert stats["uptime"] is None
        assert stats["status"] == MCPServerStatus.STOPPED.value
        
        # Update stats
        adapter._messages_sent = 5
        adapter._messages_received = 3
        adapter._bytes_sent = 1024
        adapter._bytes_received = 512
        
        stats = adapter.stats
        assert stats["messages_sent"] == 5
        assert stats["messages_received"] == 3
        assert stats["bytes_sent"] == 1024
        assert stats["bytes_received"] == 512
