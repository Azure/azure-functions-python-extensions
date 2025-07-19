# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Test module for MCP (Model Context Protocol) functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from azurefunctions.agents.mcp.server import (
    MCPServer,
    MCPServerStdioParams,
    MCPServerSseParams,
    MCPServerStreamableHttpParams
)
from azurefunctions.agents.mcp.result_formatter import MCPResultFormatter
from azurefunctions.agents.mcp.util import MCPUtil
from azurefunctions.agents.types import MCPConfig, MCPServerMode


class TestMCPServerParams:
    """Test MCP server parameter types."""

    def test_stdio_params_creation(self):
        """Test MCPServerStdioParams creation."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"],
            env={"MCP_DEBUG": "1"},
            cwd="/tmp"
        )

        assert params["command"] == "python"
        assert params["args"] == ["-m", "weather_server"]
        assert params["env"] == {"MCP_DEBUG": "1"}
        assert params["cwd"] == "/tmp"

    def test_sse_params_creation(self):
        """Test MCPServerSseParams creation."""
        params = MCPServerSseParams(
            url="http://localhost:8080/sse",
            headers={"Authorization": "Bearer token"},
            timeout=30.0
        )

        assert params["url"] == "http://localhost:8080/sse"
        assert params["headers"] == {"Authorization": "Bearer token"}
        assert params["timeout"] == 30.0

    def test_streamable_http_params_creation(self):
        """Test MCPServerStreamableHttpParams creation."""
        params = MCPServerStreamableHttpParams(
            session_url="http://localhost:8080/session",
            headers={"Content-Type": "application/json"},
            timeout=60.0
        )

        assert params["session_url"] == "http://localhost:8080/session"
        assert params["headers"] == {"Content-Type": "application/json"}
        assert params["timeout"] == 60.0


class TestMCPServer:
    """Test MCPServer functionality."""

    def test_mcp_server_stdio_initialization(self):
        """Test MCP server initialization with STDIO mode."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        assert server.name == "weather_server"
        assert server.mode == MCPServerMode.STDIO
        assert server.params == params
        assert server.session is None

    def test_mcp_server_sse_initialization(self):
        """Test MCP server initialization with SSE mode."""
        params = MCPServerSseParams(
            url="http://localhost:8080/sse"
        )

        server = MCPServer(
            name="sse_server",
            mode=MCPServerMode.SSE,
            params=params
        )

        assert server.name == "sse_server"
        assert server.mode == MCPServerMode.SSE
        assert server.params == params

    def test_mcp_server_streamable_http_initialization(self):
        """Test MCP server initialization with Streamable HTTP mode."""
        params = MCPServerStreamableHttpParams(
            session_url="http://localhost:8080/session"
        )

        server = MCPServer(
            name="http_server",
            mode=MCPServerMode.STREAMABLE_HTTP,
            params=params
        )

        assert server.name == "http_server"
        assert server.mode == MCPServerMode.STREAMABLE_HTTP
        assert server.params == params

    def test_mcp_server_invalid_mode_params(self):
        """Test MCP server with invalid parameters for mode."""
        # STDIO mode requires 'command' parameter
        with pytest.raises(ValueError, match="STDIO mode requires"):
            MCPServer(
                name="invalid_server",
                mode=MCPServerMode.STDIO,
                params={"invalid": "params"}
            )

        # SSE mode requires 'url' parameter
        with pytest.raises(ValueError, match="SSE mode requires"):
            MCPServer(
                name="invalid_server",
                mode=MCPServerMode.SSE,
                params={"invalid": "params"}
            )

        # STREAMABLE_HTTP mode requires 'session_url' parameter
        with pytest.raises(ValueError, match="STREAMABLE_HTTP mode requires"):
            MCPServer(
                name="invalid_server",
                mode=MCPServerMode.STREAMABLE_HTTP,
                params={"invalid": "params"}
            )

    @pytest.mark.skip(reason="Complex connection mocking - tested via integration tests")
    @pytest.mark.asyncio
    async def test_mcp_server_connect_stdio(self):
        """Test MCP server connection with STDIO mode."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        # Mock the STDIO connection process
        with patch('azurefunctions.agents.mcp.server.stdio_client') as mock_stdio:
            # stdio_client should return an async context manager that yields read/write streams
            mock_read_stream = Mock()
            mock_write_stream = Mock()
            mock_context = Mock()
            mock_context.__aenter__ = AsyncMock(return_value=(mock_read_stream, mock_write_stream))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_stdio.return_value = mock_context

            # Mock ClientSession creation
            with patch('azurefunctions.agents.mcp.server.ClientSession') as mock_client_session:
                mock_session = AsyncMock()
                mock_client_session.return_value = mock_session

                await server.connect()

                assert server.session is not None
                mock_stdio.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_server_double_connect(self):
        """Test that connecting twice doesn't create multiple connections."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        # Mock session
        mock_session = AsyncMock()
        server.session = mock_session

        # Second connect should return early
        await server.connect()

        assert server.session is mock_session

    @pytest.mark.asyncio
    async def test_mcp_server_list_tools(self):
        """Test listing tools from MCP server."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        # Mock session with tools - create proper Mock objects with name properties
        mock_session = AsyncMock()
        mock_tool1 = Mock()
        mock_tool1.name = "get_weather"
        mock_tool1.description = "Get weather information"

        mock_tool2 = Mock()
        mock_tool2.name = "get_forecast"
        mock_tool2.description = "Get weather forecast"

        mock_tools = [mock_tool1, mock_tool2]
        mock_list_result = Mock()
        mock_list_result.tools = mock_tools
        mock_session.list_tools.return_value = mock_list_result
        server.session = mock_session

        tools = await server.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "get_weather"
        assert tools[1].name == "get_forecast"
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_server_call_tool(self):
        """Test calling a tool on MCP server."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        # Mock session and tool call
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(type="text", text="Weather: Sunny, 25°C")]
        mock_session.call_tool.return_value = mock_result
        server.session = mock_session

        result = await server.call_tool("get_weather", {"city": "Seattle"})

        assert result == mock_result
        mock_session.call_tool.assert_called_once_with("get_weather", {"city": "Seattle"})

    @pytest.mark.asyncio
    async def test_mcp_server_cleanup(self):
        """Test cleaning up MCP server."""
        params = MCPServerStdioParams(
            command="python",
            args=["-m", "weather_server"]
        )

        server = MCPServer(
            name="weather_server",
            mode=MCPServerMode.STDIO,
            params=params
        )

        # Mock cleanup context
        mock_cleanup = AsyncMock()
        server._cleanup_context = mock_cleanup
        server.session = Mock()

        await server.cleanup()

        assert server.session is None
        assert server._cleanup_context is None
        mock_cleanup.aclose.assert_called_once()


class TestMCPResultFormatter:
    """Test MCP result formatting utilities."""

    def test_format_tool_result(self):
        """Test formatting tool results."""
        # Mock text content
        mock_content = [Mock(text="Hello, world!")]
        mock_result = Mock(content=mock_content)

        result = MCPResultFormatter.format_tool_result(mock_result)

        assert result["status"] == "success"
        assert result["result"] == "Hello, world!"

    def test_format_multiple_text_results(self):
        """Test formatting multiple text results."""
        # Mock multiple text contents
        mock_content = [
            Mock(text="Part 1"),
            Mock(text="Part 2"),
            Mock(text="Part 3")
        ]
        mock_result = Mock(content=mock_content)

        result = MCPResultFormatter.format_tool_result(mock_result)

        assert result["status"] == "success"
        assert result["result"] == "Part 1\nPart 2\nPart 3"

    def test_format_single_text_result(self):
        """Test formatting single text result."""
        # Mock single text content
        mock_content = [Mock(text="Single result")]
        mock_result = Mock(content=mock_content)

        result = MCPResultFormatter.format_tool_result(mock_result)

        assert result["status"] == "success"
        assert result["result"] == "Single result"

    def test_format_empty_result(self):
        """Test formatting empty results."""
        mock_result = Mock(content=[])

        result = MCPResultFormatter.format_tool_result(mock_result)

        assert result["status"] == "success"

    def test_format_error_handling(self):
        """Test error handling in result formatting."""
        # Mock malformed result
        mock_result = "invalid_result_format"

        result = MCPResultFormatter.format_tool_result(mock_result)

        assert result["status"] == "success"
        assert isinstance(result["result"], str)


class TestMCPUtil:
    """Test MCP utility functions."""

    @pytest.mark.asyncio
    async def test_get_function_tools(self):
        """Test getting function tools from MCP server."""
        # Mock server
        mock_server = Mock()
        mock_server.name = "test_server"

        # Mock MCP tools
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "test_tool"
        mock_mcp_tool.description = "A test tool"
        mock_mcp_tool.inputSchema = {"type": "object", "properties": {"param": {"type": "string"}}}

        mock_server.list_tools = AsyncMock(return_value=[mock_mcp_tool])

        tools = await MCPUtil.get_function_tools(mock_server)

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "A test tool"
        assert tools[0].server == mock_server

    def test_to_function_tool(self):
        """Test converting MCP tool to framework tool."""
        # Mock MCP tool
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "test_tool"
        mock_mcp_tool.description = "A test tool"
        mock_mcp_tool.inputSchema = {"type": "object", "properties": {"param": {"type": "string"}}}

        # Mock server
        mock_server = Mock()
        mock_server.name = "test_server"

        framework_tool = MCPUtil.to_function_tool(mock_mcp_tool, mock_server)

        assert framework_tool.name == "test_tool"
        assert framework_tool.description == "A test tool"
        assert framework_tool.server == mock_server
        assert framework_tool.mcp_tool == mock_mcp_tool
        assert framework_tool.parameters_schema["type"] == "object"

    @pytest.mark.asyncio
    async def test_invoke_mcp_tool(self):
        """Test invoking an MCP tool."""
        # Mock server
        mock_server = Mock()
        mock_result = Mock()
        mock_server.call_tool = AsyncMock(return_value=mock_result)

        # Mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"

        # Mock the result formatter
        with patch('azurefunctions.agents.mcp.util.MCPResultFormatter.format_tool_result_as_string') as mock_formatter:
            mock_formatter.return_value = "formatted_result"

            result = await MCPUtil.invoke_mcp_tool(mock_server, mock_tool, '{"param": "value"}')

            assert result == "formatted_result"
            mock_server.call_tool.assert_called_once_with("test_tool", {"param": "value"})
            mock_formatter.assert_called_once_with(mock_result)

    def test_convert_mcp_tools_to_llm_schema(self):
        """Test converting MCP tools to LLM schema."""
        # Mock MCP tools
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool1.description = "Tool 1"
        mock_tool1.parameters_schema = {"type": "object", "properties": {}}

        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        mock_tool2.description = "Tool 2"
        mock_tool2.parameters_schema = {"type": "object", "properties": {"param": {"type": "string"}}}

        tools = [mock_tool1, mock_tool2]

        llm_schema = MCPUtil.convert_mcp_tools_to_llm_schema(tools)

        assert len(llm_schema) == 2
        assert llm_schema[0]["type"] == "function"
        assert llm_schema[0]["function"]["name"] == "tool1"
        assert llm_schema[1]["function"]["name"] == "tool2"

    @pytest.mark.asyncio
    async def test_cleanup_servers(self):
        """Test cleaning up MCP servers."""
        # Mock servers
        mock_server1 = Mock()
        mock_server1.name = "server1"
        mock_server1.cleanup = AsyncMock()

        mock_server2 = Mock()
        mock_server2.name = "server2"
        mock_server2.cleanup = AsyncMock()

        servers = [mock_server1, mock_server2]

        await MCPUtil.cleanup_servers(servers)

        mock_server1.cleanup.assert_called_once()
        mock_server2.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_servers(self):
        """Test connecting to MCP servers."""
        # Mock servers
        mock_server1 = Mock()
        mock_server1.name = "server1"
        mock_server1.connect = AsyncMock()

        mock_server2 = Mock()
        mock_server2.name = "server2"
        mock_server2.connect = AsyncMock()

        servers = [mock_server1, mock_server2]

        await MCPUtil.connect_servers(servers)

        mock_server1.connect.assert_called_once()
        mock_server2.connect.assert_called_once()


class TestMCPConfig:
    """Test MCP configuration handling."""

    def test_mcp_config_creation(self):
        """Test creating MCP configuration."""
        config = MCPConfig(enabled=True, timeout=60, max_retries=5)

        assert config.enabled is True
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_mcp_config_defaults(self):
        """Test MCP configuration with default values."""
        config = MCPConfig()

        assert config.enabled is True
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_mcp_config_disabled(self):
        """Test creating disabled MCP configuration."""
        config = MCPConfig(enabled=False)

        assert config.enabled is False
        assert config.timeout == 30  # Default value
        assert config.max_retries == 3  # Default value
