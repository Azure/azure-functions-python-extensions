"""Unit tests for Azure Functions Agent Framework MCP integration.

This module tests the Model Context Protocol (MCP) integration including
server management, tool discovery, and communication protocols.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from azurefunctions.agents.types import MCPServerMode, MCPConfig
from azurefunctions.agents.mcp.server import (
    MCPServer,
    MCPServerStdioParams,
    MCPServerSseParams,
    MCPServerStreamableHttpParams
)
from azurefunctions.agents.mcp.util import MCPUtil
from azurefunctions.agents.mcp.result_formatter import MCPResultFormatter


class TestMCPServer:
    """Test MCP server implementations."""

    def test_mcp_server_stdio_params(self):
        """Test MCPServerStdioParams creation."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "mcp_server"],
            env={"MCP_DEBUG": "1"}
        )
        
        assert params.command == "python"
        assert params.args == ["-m", "mcp_server"]
        assert params.env == {"MCP_DEBUG": "1"}

    def test_mcp_server_sse_params(self):
        """Test MCPServerSseParams creation."""
        params = MCPServerSseParams(
            url="http://localhost:8080/sse",
            headers={"Authorization": "Bearer token123"}
        )
        
        assert params.url == "http://localhost:8080/sse"
        assert params.headers == {"Authorization": "Bearer token123"}

    def test_mcp_server_streamable_http_params(self):
        """Test MCPServerStreamableHttpParams creation."""
        params = MCPServerStreamableHttpParams(
            url="http://localhost:8080/stream",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        assert params.url == "http://localhost:8080/stream"
        assert params.headers == {"Content-Type": "application/json"}
        assert params.method == "POST"

    def test_mcp_server_stdio_initialization(self):
        """Test MCP server initialization with stdio mode."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )
        
        server = MCPServer(
            name="weather-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        assert server.name == "weather-server"
        assert server.mode == MCPServerMode.STDIO
        assert server.params == params
        assert server.connected is False

    def test_mcp_server_sse_initialization(self):
        """Test MCP server initialization with SSE mode."""
        params = MCPServerSseParams(
            url="http://localhost:8080/sse"
        )
        
        server = MCPServer(
            name="web-tools",
            mode=MCPServerMode.SSE,
            params=params
        )
        
        assert server.name == "web-tools"
        assert server.mode == MCPServerMode.SSE
        assert server.params == params
        assert server.connected is False

    def test_mcp_server_streamable_http_initialization(self):
        """Test MCP server initialization with streamable HTTP mode."""
        params = MCPServerStreamableHttpParams(
            url="http://localhost:8080/stream"
        )
        
        server = MCPServer(
            name="api-tools",
            mode=MCPServerMode.STREAMABLE_HTTP,
            params=params
        )
        
        assert server.name == "api-tools"
        assert server.mode == MCPServerMode.STREAMABLE_HTTP
        assert server.params == params
        assert server.connected is False

    @pytest.mark.asyncio
    async def test_mcp_server_connect_stdio(self):
        """Test MCP server connection in stdio mode."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        with patch('azurefunctions.agents.mcp.server.mcp') as mock_mcp:
            mock_client = AsyncMock()
            mock_mcp.ClientSession.return_value.__aenter__.return_value = mock_client
            mock_mcp.stdio_client.return_value = Mock()
            
            await server.connect()
            
            assert server.connected is True
            assert server.client is not None

    @pytest.mark.asyncio
    async def test_mcp_server_connect_sse(self):
        """Test MCP server connection in SSE mode."""
        params = MCPServerSseParams(
            url="http://localhost:8080/sse"
        )
        
        server = MCPServer(
            name="sse-server",
            mode=MCPServerMode.SSE,
            params=params
        )
        
        with patch('azurefunctions.agents.mcp.server.mcp') as mock_mcp:
            mock_client = AsyncMock()
            mock_mcp.ClientSession.return_value.__aenter__.return_value = mock_client
            mock_mcp.sse_client.return_value = Mock()
            
            await server.connect()
            
            assert server.connected is True
            assert server.client is not None

    @pytest.mark.asyncio
    async def test_mcp_server_connect_streamable_http(self):
        """Test MCP server connection in streamable HTTP mode."""
        params = MCPServerStreamableHttpParams(
            url="http://localhost:8080/stream"
        )
        
        server = MCPServer(
            name="http-server",
            mode=MCPServerMode.STREAMABLE_HTTP,
            params=params
        )
        
        with patch('azurefunctions.agents.mcp.server.mcp') as mock_mcp:
            mock_client = AsyncMock()
            mock_mcp.ClientSession.return_value.__aenter__.return_value = mock_client
            mock_mcp.streamable_http_client.return_value = Mock()
            
            await server.connect()
            
            assert server.connected is True
            assert server.client is not None

    @pytest.mark.asyncio
    async def test_mcp_server_disconnect(self):
        """Test MCP server disconnection."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        # Mock connected state
        server.connected = True
        server.client = AsyncMock()
        server.session = AsyncMock()
        
        await server.disconnect()
        
        assert server.connected is False
        assert server.client is None
        assert server.session is None

    @pytest.mark.asyncio
    async def test_mcp_server_list_tools(self):
        """Test listing tools from MCP server."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )
        
        server = MCPServer(
            name="weather-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        # Mock client and tools response
        mock_client = AsyncMock()
        server.client = mock_client
        server.connected = True
        
        mock_tools_response = Mock()
        mock_tools_response.tools = [
            Mock(name="get_weather", description="Get weather information"),
            Mock(name="get_forecast", description="Get weather forecast")
        ]
        
        mock_client.list_tools.return_value = mock_tools_response
        
        tools = await server.list_tools()
        
        assert len(tools) == 2
        assert tools[0].name == "get_weather"
        assert tools[1].name == "get_forecast"
        
        mock_client.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_server_call_tool(self):
        """Test calling a tool on MCP server."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )
        
        server = MCPServer(
            name="weather-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        # Mock client and tool response
        mock_client = AsyncMock()
        server.client = mock_client
        server.connected = True
        
        mock_tool_response = Mock()
        mock_tool_response.content = [
            Mock(type="text", text='{"temperature": 72, "condition": "sunny"}')
        ]
        
        mock_client.call_tool.return_value = mock_tool_response
        
        result = await server.call_tool(
            "get_weather",
            {"city": "San Francisco"}
        )
        
        assert result is not None
        assert mock_client.call_tool.called
        
        # Verify call_tool was called with correct arguments
        call_args = mock_client.call_tool.call_args
        assert call_args[1]["name"] == "get_weather"
        assert call_args[1]["arguments"] == {"city": "San Francisco"}

    @pytest.mark.asyncio
    async def test_mcp_server_call_tool_not_connected(self):
        """Test calling tool when server is not connected."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        # Server not connected
        assert server.connected is False
        
        with pytest.raises(RuntimeError, match="not connected"):
            await server.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_mcp_server_connection_error_handling(self):
        """Test MCP server connection error handling."""
        params = MCPServerStdioParams(
            command="nonexistent_command",
            args=["--invalid"]
        )
        
        server = MCPServer(
            name="invalid-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        with patch('azurefunctions.agents.mcp.server.mcp') as mock_mcp:
            mock_mcp.stdio_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                await server.connect()
            
            assert server.connected is False

    def test_mcp_server_string_representation(self):
        """Test MCP server string representation."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        str_repr = str(server)
        assert "test-server" in str_repr
        assert "STDIO" in str_repr


class TestMCPUtil:
    """Test MCP utility functions."""

    def test_mcp_util_initialization(self):
        """Test MCPUtil initialization."""
        util = MCPUtil()
        assert hasattr(util, 'servers')
        assert len(util.servers) == 0

    def test_mcp_util_add_server(self):
        """Test adding server to MCPUtil."""
        util = MCPUtil()
        
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        util.add_server(server)
        
        assert len(util.servers) == 1
        assert "test-server" in util.servers
        assert util.servers["test-server"] == server

    def test_mcp_util_get_server(self):
        """Test getting server from MCPUtil."""
        util = MCPUtil()
        
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )
        
        server = MCPServer(
            name="weather-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        util.add_server(server)
        
        retrieved_server = util.get_server("weather-server")
        assert retrieved_server == server
        
        # Test non-existent server
        missing_server = util.get_server("non-existent")
        assert missing_server is None

    def test_mcp_util_remove_server(self):
        """Test removing server from MCPUtil."""
        util = MCPUtil()
        
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "test_server"]
        )
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=params
        )
        
        util.add_server(server)
        assert len(util.servers) == 1
        
        removed_server = util.remove_server("test-server")
        assert removed_server == server
        assert len(util.servers) == 0
        
        # Test removing non-existent server
        missing_server = util.remove_server("non-existent")
        assert missing_server is None

    @pytest.mark.asyncio
    async def test_mcp_util_connect_all_servers(self):
        """Test connecting all servers in MCPUtil."""
        util = MCPUtil()
        
        # Add multiple servers
        for i in range(3):
            params = MCPServerStdioParams(
                command="python",
                args=["-m", f"server_{i}"]
            )
            
            server = MCPServer(
                name=f"server-{i}",
                mode=MCPServerMode.STDIO,
                params=params
            )
            
            # Mock the connect method
            server.connect = AsyncMock()
            util.add_server(server)
        
        await util.connect_all_servers()
        
        # Verify all servers were connected
        for server in util.servers.values():
            server.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_util_disconnect_all_servers(self):
        """Test disconnecting all servers in MCPUtil."""
        util = MCPUtil()
        
        # Add multiple servers
        for i in range(3):
            params = MCPServerStdioParams(
                command="python",
                args=["-m", f"server_{i}"]
            )
            
            server = MCPServer(
                name=f"server-{i}",
                mode=MCPServerMode.STDIO,
                params=params
            )
            
            # Mock the disconnect method
            server.disconnect = AsyncMock()
            server.connected = True
            util.add_server(server)
        
        await util.disconnect_all_servers()
        
        # Verify all servers were disconnected
        for server in util.servers.values():
            server.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_util_list_all_tools(self):
        """Test listing tools from all connected servers."""
        util = MCPUtil()
        
        # Add servers with mock tools
        server1 = MCPServer(
            name="weather-server",
            mode=MCPServerMode.STDIO,
            params=MCPServerStdioParams(command="python", args=["-m", "weather"])
        )
        server1.connected = True
        server1.list_tools = AsyncMock(return_value=[
            Mock(name="get_weather", description="Get weather"),
            Mock(name="get_forecast", description="Get forecast")
        ])
        
        server2 = MCPServer(
            name="web-server",
            mode=MCPServerMode.SSE,
            params=MCPServerSseParams(url="http://localhost:8080/sse")
        )
        server2.connected = True
        server2.list_tools = AsyncMock(return_value=[
            Mock(name="search_web", description="Search the web")
        ])
        
        util.add_server(server1)
        util.add_server(server2)
        
        all_tools = await util.list_all_tools()
        
        assert len(all_tools) == 3
        tool_names = [tool.name for tool in all_tools]
        assert "get_weather" in tool_names
        assert "get_forecast" in tool_names
        assert "search_web" in tool_names

    @pytest.mark.asyncio
    async def test_mcp_util_call_tool_on_server(self):
        """Test calling tool on specific server via MCPUtil."""
        util = MCPUtil()
        
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=MCPServerStdioParams(command="python", args=["-m", "test"])
        )
        server.connected = True
        server.call_tool = AsyncMock(return_value={"result": "success"})
        
        util.add_server(server)
        
        result = await util.call_tool_on_server(
            "test-server",
            "test_tool",
            {"param": "value"}
        )
        
        assert result == {"result": "success"}
        server.call_tool.assert_called_once_with("test_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_mcp_util_call_tool_server_not_found(self):
        """Test calling tool on non-existent server."""
        util = MCPUtil()
        
        with pytest.raises(ValueError, match="Server .* not found"):
            await util.call_tool_on_server(
                "non-existent-server",
                "test_tool",
                {}
            )


class TestMCPResultFormatter:
    """Test MCP result formatting utilities."""

    def test_mcp_result_formatter_initialization(self):
        """Test MCPResultFormatter initialization."""
        formatter = MCPResultFormatter()
        assert hasattr(formatter, 'format_tool_result')

    def test_mcp_result_formatter_text_content(self):
        """Test formatting text content from MCP tool result."""
        formatter = MCPResultFormatter()
        
        mock_content = [
            Mock(type="text", text="Weather: 72°F, sunny")
        ]
        
        result = formatter.format_tool_result(mock_content)
        
        assert result == "Weather: 72°F, sunny"

    def test_mcp_result_formatter_json_content(self):
        """Test formatting JSON content from MCP tool result."""
        formatter = MCPResultFormatter()
        
        mock_content = [
            Mock(type="text", text='{"temperature": 72, "condition": "sunny"}')
        ]
        
        result = formatter.format_tool_result(mock_content)
        
        # Should return the JSON string as-is
        assert result == '{"temperature": 72, "condition": "sunny"}'

    def test_mcp_result_formatter_multiple_content_items(self):
        """Test formatting multiple content items."""
        formatter = MCPResultFormatter()
        
        mock_content = [
            Mock(type="text", text="Temperature: 72°F"),
            Mock(type="text", text="Condition: sunny"),
            Mock(type="text", text="Humidity: 65%")
        ]
        
        result = formatter.format_tool_result(mock_content)
        
        # Should concatenate all text content
        expected = "Temperature: 72°F\nCondition: sunny\nHumidity: 65%"
        assert result == expected

    def test_mcp_result_formatter_empty_content(self):
        """Test formatting empty content."""
        formatter = MCPResultFormatter()
        
        result = formatter.format_tool_result([])
        
        assert result == ""

    def test_mcp_result_formatter_non_text_content(self):
        """Test formatting non-text content types."""
        formatter = MCPResultFormatter()
        
        mock_content = [
            Mock(type="image", data="base64_image_data"),
            Mock(type="text", text="Image description: A sunny day")
        ]
        
        result = formatter.format_tool_result(mock_content)
        
        # Should only include text content
        assert result == "Image description: A sunny day"

    def test_mcp_result_formatter_error_content(self):
        """Test formatting error content."""
        formatter = MCPResultFormatter()
        
        mock_content = [
            Mock(type="text", text="Error: Unable to fetch weather data")
        ]
        
        result = formatter.format_tool_result(mock_content)
        
        assert result == "Error: Unable to fetch weather data"


class TestMCPIntegration:
    """Test MCP integration with agent framework."""

    def test_mcp_config_validation(self):
        """Test MCP configuration validation."""
        config = MCPConfig(
            enabled=True,
            timeout=60,
            max_retries=5
        )
        
        assert config.enabled is True
        assert config.timeout == 60
        assert config.max_retries == 5

    @pytest.mark.asyncio
    async def test_agent_with_mcp_servers(self):
        """Test agent integration with MCP servers."""
        # This would typically be tested in the agent tests,
        # but we'll include a basic integration test here
        
        mcp_servers = [
            MCPServer(
                name="weather-server",
                mode=MCPServerMode.STDIO,
                params=MCPServerStdioParams(
                    command="python",
                    args=["-m", "weather_server"]
                )
            ),
            MCPServer(
                name="web-server", 
                mode=MCPServerMode.SSE,
                params=MCPServerSseParams(
                    url="http://localhost:8080/sse"
                )
            )
        ]
        
        # Mock agent with MCP servers
        mock_agent = Mock()
        mock_agent.mcp_servers = mcp_servers
        mock_agent.name = "TestAgent"
        
        # Verify servers are properly configured
        assert len(mock_agent.mcp_servers) == 2
        assert mock_agent.mcp_servers[0].name == "weather-server"
        assert mock_agent.mcp_servers[1].name == "web-server"
        assert mock_agent.mcp_servers[0].mode == MCPServerMode.STDIO
        assert mock_agent.mcp_servers[1].mode == MCPServerMode.SSE

    @pytest.mark.asyncio
    async def test_mcp_tool_discovery_and_execution(self):
        """Test MCP tool discovery and execution workflow."""
        util = MCPUtil()
        formatter = MCPResultFormatter()
        
        # Setup mock server with tools
        server = MCPServer(
            name="test-server",
            mode=MCPServerMode.STDIO,
            params=MCPServerStdioParams(command="python", args=["-m", "test"])
        )
        
        # Mock server methods
        server.connected = True
        server.list_tools = AsyncMock(return_value=[
            Mock(name="calculator", description="Perform calculations"),
            Mock(name="text_analyzer", description="Analyze text")
        ])
        server.call_tool = AsyncMock(return_value=Mock(
            content=[Mock(type="text", text="Result: 42")]
        ))
        
        util.add_server(server)
        
        # Test tool discovery
        tools = await server.list_tools()
        assert len(tools) == 2
        assert tools[0].name == "calculator"
        
        # Test tool execution
        result = await server.call_tool("calculator", {"expression": "6 * 7"})
        formatted_result = formatter.format_tool_result(result.content)
        
        assert formatted_result == "Result: 42"
        
        # Verify call was made correctly
        server.call_tool.assert_called_once_with("calculator", {"expression": "6 * 7"})
