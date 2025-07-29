"""
Integration tests for MCP Function App.

These tests verify the end-to-end functionality of the MCP adapter,
including HTTP endpoint creation and STDIO communication.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from azure.functions import HttpRequest, HttpMethod
from azurefunctions.extensions.mcp_server import (
    MCPFunctionApp,
    MCPMode,
    MCPStdioConfiguration,
    MCPServerStdioParams,
)
from tests.conftest import AsyncTestCase


class TestMCPFunctionAppIntegration(AsyncTestCase):
    """Integration tests for MCPFunctionApp."""
    
    async def test_app_initialization_with_config(self, sample_mcp_config, mock_shutil_which):
        """Test app initialization with programmatic configuration."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        assert app.mode == MCPMode.STDIO
        assert app.current_server_config == sample_mcp_config
        assert app.multi_config is not None
        assert len(app.multi_config.servers) == 1
    
    async def test_app_initialization_with_file(self, temp_config_file, mock_shutil_which):
        """Test app initialization with configuration file."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            config_file=str(temp_config_file)
        )
        
        assert app.mode == MCPMode.STDIO
        assert app.current_server_config is not None
        assert app.current_server_config.name == "test-server"
        assert app.multi_config is not None
    
    async def test_app_initialization_well_known_file(self, sample_config_data_format1, mock_shutil_which):
        """Test app initialization with well-known configuration file."""
        # Create a temporary mcp_config.json in current directory
        config_path = Path.cwd() / "mcp_config.json"
        
        try:
            with config_path.open('w') as f:
                json.dump(sample_config_data_format1, f)
            
            app = MCPFunctionApp(mode=MCPMode.STDIO)
            
            assert app.current_server_config is not None
            assert app.current_server_config.name == "test-server"
            
        finally:
            # Clean up
            if config_path.exists():
                config_path.unlink()
    
    async def test_app_initialization_no_config(self):
        """Test app initialization failure when no configuration is found."""
        with pytest.raises(ValueError, match="No MCP server configuration found"):
            MCPFunctionApp(mode=MCPMode.STDIO)
    
    async def test_http_endpoint_creation(self, sample_mcp_config, mock_shutil_which):
        """Test that HTTP endpoint is created correctly."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        # The app should have the mcp function registered
        # This is a basic check - in real scenario we'd test the actual endpoint
        assert hasattr(app, '_function_definitions')
    
    @pytest.mark.skip(reason="Requires Azure Functions runtime simulation")
    async def test_mcp_endpoint_request_handling(self, sample_mcp_config, mock_shutil_which):
        """Test MCP endpoint request handling."""
        # This test would require more complex setup to simulate
        # Azure Functions HTTP request handling
        pass
    
    async def test_ensure_connection_success(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test successful connection establishment."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            success = await app._ensure_connection()
            
            assert success
            assert app.stdio_adapter is not None
            assert app.stdio_adapter.is_connected
    
    async def test_ensure_connection_failure(self, sample_mcp_config):
        """Test connection failure handling."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        # Mock the stdio adapter connect to fail
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch.object(app, 'stdio_adapter', None):
                # Create a mock adapter that fails to connect
                mock_adapter = AsyncMock()
                mock_adapter.is_connected = False
                mock_adapter.connect = AsyncMock(return_value=False)
                
                app.stdio_adapter = mock_adapter
                
                success = await app._ensure_connection()
                
                assert not success
    
    async def test_cleanup(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test cleanup functionality."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            # Establish connection first
            await app._ensure_connection()
            assert app.stdio_adapter is not None
            
            # Cleanup
            await app.cleanup()
            
            assert app.stdio_adapter is None
    
    async def test_get_server_stats_no_adapter(self, sample_mcp_config):
        """Test getting stats when no adapter is initialized."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        stats = app.get_server_stats()
        
        assert stats["status"] == "not_initialized"
    
    async def test_get_server_stats_with_adapter(self, sample_mcp_config, mock_asyncio_create_subprocess_exec):
        """Test getting stats with initialized adapter."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await app._ensure_connection()
            
            stats = app.get_server_stats()
            
            assert "server_name" in stats
            assert "mode" in stats
            assert "status" in stats
            assert stats["server_name"] == "test-server"
            assert stats["mode"] == "stdio"
    
    async def test_convert_request_to_scope(self, sample_mcp_config):
        """Test conversion of Azure Functions request to ASGI scope."""
        app = MCPFunctionApp(
            mode=MCPMode.STDIO,
            mcp_server=sample_mcp_config
        )
        
        # Create a mock HttpRequest
        mock_request = HttpRequest(
            method="POST",
            url="https://myapp.azurewebsites.net/api/mcp",
            headers={"Content-Type": "application/json"},
            params={},
            route_params={"path": "/mcp"}
        )
        
        scope = app._convert_request_to_scope(mock_request)
        
        assert scope["type"] == "http"
        assert scope["method"] == "POST"
        assert scope["scheme"] == "https"
        assert scope["path"] == "/mcp"
        assert ("content-type", b"application/json") in scope["headers"]
    
    async def test_multiple_configuration_formats(self, mock_shutil_which):
        """Test that all configuration formats are supported."""
        configs = [
            {
                "mcpServers": {
                    "test1": {
                        "command": "echo",
                        "args": ["test1"]
                    }
                }
            },
            {
                "servers": {
                    "test2": {
                        "type": "stdio",
                        "command": "echo",
                        "args": ["test2"]
                    }
                }
            },
            {
                "mcp": {
                    "server": {
                        "test3": {
                            "command": "echo",
                            "args": ["test3"]
                        }
                    }
                }
            }
        ]
        
        for i, config_data in enumerate(configs):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config_data, f)
                config_file = f.name
            
            try:
                app = MCPFunctionApp(
                    mode=MCPMode.STDIO,
                    config_file=config_file
                )
                
                assert app.current_server_config is not None
                expected_name = f"test{i+1}"
                assert app.current_server_config.name == expected_name
                
            finally:
                Path(config_file).unlink()
    
    async def test_error_handling_invalid_config_file(self):
        """Test error handling for invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            config_file = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                MCPFunctionApp(
                    mode=MCPMode.STDIO,
                    config_file=config_file
                )
        finally:
            Path(config_file).unlink()
    
    async def test_error_handling_missing_config_file(self):
        """Test error handling for missing configuration file."""
        with pytest.raises(FileNotFoundError):
            MCPFunctionApp(
                mode=MCPMode.STDIO,
                config_file="/non/existent/path.json"
            )
