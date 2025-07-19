# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Test module for tools functionality."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from azurefunctions.agents.tools.tool_registry import ToolRegistry
from azurefunctions.agents.tools.function_tools import FunctionToolManager
from azurefunctions.agents.tools.mcp_tools import MCPToolManager
from azurefunctions.agents.types import MCPConfig, MCPServerMode


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_tool_registry_initialization(self):
        """Test that ToolRegistry can be initialized."""
        registry = ToolRegistry()

        assert registry is not None
        assert hasattr(registry, 'function_manager')
        assert hasattr(registry, 'mcp_manager')
        assert isinstance(registry.function_manager, FunctionToolManager)

    def test_function_tool_registration(self):
        """Test registering function tools."""
        registry = ToolRegistry()

        def sample_tool(param1: str, param2: int = 5) -> str:
            """A sample tool for testing."""
            return f"Result: {param1}-{param2}"

        result = registry.register_function_tool("sample_tool", sample_tool)
        assert result is True

        # Check the tool was registered in the function manager
        tools = registry.function_manager.list_tools()
        tool_names = [tool['name'] for tool in tools]
        assert "sample_tool" in tool_names

    @pytest.mark.asyncio
    async def test_function_tool_execution(self):
        """Test executing function tools."""
        registry = ToolRegistry()

        def sample_tool(param1: str, param2: int = 5) -> str:
            """A sample tool for testing."""
            return f"Result: {param1}-{param2}"

        registry.register_function_tool("sample_tool", sample_tool)

        result = await registry.execute_tool("sample_tool", {"param1": "test", "param2": 10})

        assert result["status"] == "success"
        assert result["result"] == "Result: test-10"

    @pytest.mark.asyncio
    async def test_async_function_tool_execution(self):
        """Test executing async function tools."""
        registry = ToolRegistry()

        async def async_sample_tool(param1: str) -> str:
            """An async sample tool for testing."""
            await asyncio.sleep(0.01)  # Simulate async work
            return f"Async result: {param1}"

        registry.register_function_tool("async_sample_tool", async_sample_tool)

        result = await registry.execute_tool("async_sample_tool", {"param1": "test"})

        assert result["status"] == "success"
        assert result["result"] == "Async result: test"

    def test_tool_listing(self):
        """Test listing all available tools."""
        registry = ToolRegistry()

        def tool1() -> str:
            """Tool 1."""
            return "tool1"

        def tool2() -> str:
            """Tool 2."""
            return "tool2"

        registry.register_function_tool("tool1", tool1)
        registry.register_function_tool("tool2", tool2)

        all_tools = registry.list_all_tools()

        assert len(all_tools) >= 2
        tool_names = [tool['name'] for tool in all_tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_tool_schema_generation(self):
        """Test tool schema generation."""
        registry = ToolRegistry()

        def sample_tool(param1: str, param2: int = 5, param3: bool = False) -> str:
            """A sample tool with typed parameters.

            Args:
                param1: A required string parameter
                param2: An optional integer parameter
                param3: An optional boolean parameter
            """
            return f"Result: {param1}-{param2}-{param3}"

        registry.register_function_tool("sample_tool", sample_tool)

        schema = registry.get_tool_schema("sample_tool")

        assert schema is not None
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "sample_tool"
        assert "parameters" in schema["function"]

    def test_tools_for_llm_format(self):
        """Test getting tools in LLM format."""
        registry = ToolRegistry()

        def sample_tool(param1: str) -> str:
            """A sample tool for LLM testing."""
            return f"Result: {param1}"

        registry.register_function_tool("sample_tool", sample_tool)

        llm_tools = registry.get_tools_for_llm()

        assert isinstance(llm_tools, list)
        assert len(llm_tools) >= 1

        # Check the format is correct for LLM consumption
        sample_tool_schema = None
        for tool in llm_tools:
            if tool.get("function", {}).get("name") == "sample_tool":
                sample_tool_schema = tool
                break

        assert sample_tool_schema is not None
        assert sample_tool_schema["type"] == "function"
        assert "function" in sample_tool_schema

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""
        registry = ToolRegistry()

        def error_tool() -> str:
            """A tool that raises an error."""
            raise ValueError("Test error")

        registry.register_function_tool("error_tool", error_tool)

        result = await registry.execute_tool("error_tool", {})

        assert result["status"] == "error"
        assert "error" in result
        assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_nonexistent_tool_execution(self):
        """Test executing a tool that doesn't exist."""
        registry = ToolRegistry()

        result = await registry.execute_tool("nonexistent_tool", {})

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


class TestFunctionToolManager:
    """Test FunctionToolManager directly."""

    def test_function_tool_manager_initialization(self):
        """Test FunctionToolManager initialization."""
        manager = FunctionToolManager()

        assert manager is not None
        assert hasattr(manager, 'tools')
        assert isinstance(manager.tools, dict)

    def test_tool_registration_with_custom_params(self):
        """Test tool registration with custom parameters."""
        manager = FunctionToolManager()

        def custom_tool(x: int, y: str) -> str:
            return f"{x}: {y}"

        custom_params = {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "An integer"},
                "y": {"type": "string", "description": "A string"}
            }
        }

        result = manager.register_tool(
            "custom_tool",
            custom_tool,
            description="Custom tool",
            parameters=custom_params,
            required_params=["x", "y"]
        )

        assert result is True

        tool_def = manager.get_tool("custom_tool")
        assert tool_def is not None
        assert tool_def.name == "custom_tool"
        assert tool_def.description == "Custom tool"
        assert tool_def.parameters == custom_params
        assert tool_def.required_params == ["x", "y"]

    def test_tool_unregistration(self):
        """Test tool unregistration."""
        manager = FunctionToolManager()

        def temp_tool() -> str:
            return "temp"

        # Register and then unregister
        manager.register_tool("temp_tool", temp_tool)
        assert manager.get_tool("temp_tool") is not None

        result = manager.unregister_tool("temp_tool")
        assert result is True
        assert manager.get_tool("temp_tool") is None

        # Try to unregister again
        result = manager.unregister_tool("temp_tool")
        assert result is False


class TestMCPToolManager:
    """Test MCPToolManager functionality."""

    def test_mcp_tool_manager_initialization(self):
        """Test MCPToolManager initialization."""
        config = MCPConfig()
        manager = MCPToolManager(config)

        assert manager is not None
        assert manager.config == config
        assert hasattr(manager, 'servers')
        assert hasattr(manager, 'available_tools')

    def test_tool_name_sanitization(self):
        """Test MCP tool name sanitization."""
        # Test various problematic names
        test_cases = [
            ("tool-with-hyphens", "tool-with-hyphens"),  # Should remain unchanged
            ("tool_with_underscores", "tool_with_underscores"),  # Should remain unchanged
            ("tool with spaces", "tool_with_spaces"),
            ("tool.with.dots", "tool_with_dots"),
            ("tool@with#symbols!", "tool_with_symbols"),
            ("123tool", "_123tool"),  # Should add underscore prefix
            ("", ""),  # Edge case
            ("___multiple___underscores___", "multiple_underscores"),
        ]

        for input_name, expected in test_cases:
            result = MCPToolManager._sanitize_tool_name(input_name)
            assert result == expected, f"Failed for input '{input_name}': got '{result}', expected '{expected}'"

    @pytest.mark.asyncio
    async def test_mcp_server_addition(self):
        """Test adding MCP servers."""
        config = MCPConfig()
        manager = MCPToolManager(config)

        # Mock MCP server
        mock_server = Mock()
        mock_server.name = "test_server"
        mock_server.connect = AsyncMock()
        mock_server.list_tools = AsyncMock(return_value=[])

        result = await manager.add_server(mock_server)

        assert result is True
        assert "test_server" in manager.servers
        mock_server.connect.assert_called_once()
        mock_server.list_tools.assert_called_once()
