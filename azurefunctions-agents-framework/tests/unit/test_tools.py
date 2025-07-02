"""Unit tests for Azure Functions Agent Framework tools module.

This module tests tool management, function tools, MCP tools integration,
and the tool registry system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from azurefunctions.agents.tools.tool_registry import ToolRegistry
from azurefunctions.agents.tools.function_tools import FunctionToolManager
from azurefunctions.agents.tools.mcp_tools import MCPTool
from azurefunctions.agents.types import ToolDefinition


class TestToolRegistry:
    """Test the tool registry system."""

    def test_tool_registry_initialization(self):
        """Test ToolRegistry initialization."""
        registry = ToolRegistry()
        
        assert hasattr(registry, 'tools')
        assert len(registry.tools) == 0
        assert hasattr(registry, 'logger')

    def test_tool_registry_register_function_tool(self):
        """Test registering a function-based tool."""
        registry = ToolRegistry()
        
        def sample_function(text: str) -> str:
            """Sample function for testing."""
            return f"Processed: {text}"
        
        tool_def = ToolDefinition(
            name="sample_tool",
            description="A sample tool for testing",
            function=sample_function,
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to process"}
                },
                "required": ["text"]
            }
        )
        
        registry.register_tool(tool_def)
        
        assert "sample_tool" in registry.tools
        assert registry.tools["sample_tool"] == tool_def
        assert len(registry.tools) == 1

    def test_tool_registry_register_multiple_tools(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()
        
        def tool1(x: int) -> int:
            return x * 2
        
        def tool2(text: str) -> str:
            return text.upper()
        
        tool_def1 = ToolDefinition(
            name="double",
            description="Double a number",
            function=tool1
        )
        
        tool_def2 = ToolDefinition(
            name="uppercase",
            description="Convert text to uppercase",
            function=tool2
        )
        
        registry.register_tool(tool_def1)
        registry.register_tool(tool_def2)
        
        assert len(registry.tools) == 2
        assert "double" in registry.tools
        assert "uppercase" in registry.tools

    def test_tool_registry_register_duplicate_tool(self):
        """Test registering tool with duplicate name."""
        registry = ToolRegistry()
        
        def tool1():
            return "first"
        
        def tool2():
            return "second"
        
        tool_def1 = ToolDefinition(
            name="duplicate_tool",
            description="First tool",
            function=tool1
        )
        
        tool_def2 = ToolDefinition(
            name="duplicate_tool",
            description="Second tool",
            function=tool2
        )
        
        registry.register_tool(tool_def1)
        
        # Should overwrite the first tool
        registry.register_tool(tool_def2)
        
        assert len(registry.tools) == 1
        assert registry.tools["duplicate_tool"] == tool_def2

    def test_tool_registry_get_tool(self):
        """Test getting tool from registry."""
        registry = ToolRegistry()
        
        def sample_tool():
            return "test"
        
        tool_def = ToolDefinition(
            name="test_tool",
            description="Test tool",
            function=sample_tool
        )
        
        registry.register_tool(tool_def)
        
        retrieved_tool = registry.get_tool("test_tool")
        assert retrieved_tool == tool_def
        
        # Test non-existent tool
        missing_tool = registry.get_tool("non_existent")
        assert missing_tool is None

    def test_tool_registry_remove_tool(self):
        """Test removing tool from registry."""
        registry = ToolRegistry()
        
        def sample_tool():
            return "test"
        
        tool_def = ToolDefinition(
            name="removable_tool",
            description="Tool to be removed",
            function=sample_tool
        )
        
        registry.register_tool(tool_def)
        assert len(registry.tools) == 1
        
        removed_tool = registry.remove_tool("removable_tool")
        assert removed_tool == tool_def
        assert len(registry.tools) == 0
        
        # Test removing non-existent tool
        missing_tool = registry.remove_tool("non_existent")
        assert missing_tool is None

    def test_tool_registry_list_tools(self):
        """Test listing all tools in registry."""
        registry = ToolRegistry()
        
        # Add multiple tools
        for i in range(3):
            def tool_func():
                return f"tool_{i}"
            
            tool_def = ToolDefinition(
                name=f"tool_{i}",
                description=f"Tool number {i}",
                function=tool_func
            )
            registry.register_tool(tool_def)
        
        tool_list = registry.list_tools()
        
        assert len(tool_list) == 3
        tool_names = [tool.name for tool in tool_list]
        assert "tool_0" in tool_names
        assert "tool_1" in tool_names
        assert "tool_2" in tool_names

    def test_tool_registry_clear_tools(self):
        """Test clearing all tools from registry."""
        registry = ToolRegistry()
        
        # Add some tools
        for i in range(3):
            def tool_func():
                return f"tool_{i}"
            
            tool_def = ToolDefinition(
                name=f"tool_{i}",
                description=f"Tool {i}",
                function=tool_func
            )
            registry.register_tool(tool_def)
        
        assert len(registry.tools) == 3
        
        registry.clear_tools()
        
        assert len(registry.tools) == 0

    def test_tool_registry_has_tool(self):
        """Test checking if tool exists in registry."""
        registry = ToolRegistry()
        
        def sample_tool():
            return "test"
        
        tool_def = ToolDefinition(
            name="check_tool",
            description="Tool for checking",
            function=sample_tool
        )
        
        registry.register_tool(tool_def)
        
        assert registry.has_tool("check_tool") is True
        assert registry.has_tool("non_existent") is False


class TestFunctionToolManager:
    """Test function-based tool manager."""

    def test_function_tool_manager_creation(self):
        """Test creating FunctionToolManager."""
        manager = FunctionToolManager()
        assert manager is not None
        assert hasattr(manager, 'tools')
        assert len(manager.tools) == 0

    def test_function_tool_manager_register_tool(self):
        """Test registering a tool with FunctionToolManager."""
        manager = FunctionToolManager()
        
        def sample_function(x: int) -> int:
            """Sample function for testing."""
            return x * 2
        
        success = manager.register_tool(
            name="double_number",
            function=sample_function,
            description="Double a number"
        )
        
        assert success is True
        assert "double_number" in manager.tools
        assert manager.tools["double_number"].name == "double_number"
        assert manager.tools["double_number"].description == "Double a number"

    @pytest.mark.asyncio
    async def test_function_tool_manager_execute_tool(self):
        """Test executing a tool through FunctionToolManager."""
        manager = FunctionToolManager()
        
        def multiply(x: int, y: int) -> int:
            """Multiply two numbers."""
            return x * y
        
        manager.register_tool(
            name="multiply",
            function=multiply,
            description="Multiply two numbers"
        )
        
        result = await manager.execute_tool("multiply", {"x": 5, "y": 3})
        assert result == 15

    @pytest.mark.asyncio 
    async def test_function_tool_manager_execute_async_tool(self):
        """Test executing an async tool through FunctionToolManager."""
        manager = FunctionToolManager()
        
        async def async_add(x: int, y: int) -> int:
            """Add two numbers asynchronously."""
            return x + y
        
        manager.register_tool(
            name="async_add",
            function=async_add,
            description="Add two numbers asynchronously"
        )
        
        result = await manager.execute_tool("async_add", {"x": 10, "y": 15})
        assert result == 25

    def test_function_tool_manager_get_tool_schema(self):
        """Test getting tool schema from FunctionToolManager."""
        manager = FunctionToolManager()
        
        def sample_tool(text: str, count: int = 1) -> str:
            """Repeat text count times."""
            return text * count
        
        manager.register_tool(
            name="repeat_text",
            function=sample_tool,
            description="Repeat text multiple times"
        )
        
        schema = manager.get_tool_schema("repeat_text")
        assert schema is not None
        assert isinstance(schema, dict)

    def test_function_tool_manager_list_tools(self):
        """Test listing tools in FunctionToolManager."""
        manager = FunctionToolManager()
        
        # Add multiple tools
        for i in range(3):
            def tool_func(x: int) -> int:
                return x + i
            
            manager.register_tool(
                name=f"tool_{i}",
                function=tool_func,
                description=f"Tool number {i}"
            )
        
        tools = manager.list_tools()
        assert len(tools) == 3
        
        tool_names = [tool.name for tool in tools]
        assert "tool_0" in tool_names
        assert "tool_1" in tool_names
        assert "tool_2" in tool_names

    @pytest.mark.asyncio
    async def test_function_tool_manager_error_handling(self):
        """Test error handling in FunctionToolManager."""
        manager = FunctionToolManager()
        
        def error_tool() -> str:
            """Tool that raises an error."""
            raise ValueError("Test error")
        
        manager.register_tool(
            name="error_tool",
            function=error_tool,
            description="Tool that raises an error"
        )
        
        with pytest.raises(ValueError, match="Test error"):
            await manager.execute_tool("error_tool", {})


class TestMCPTool:
    """Test MCP-based tools."""

    def test_mcp_tool_creation(self):
        """Test creating MCPTool."""
        mock_server = Mock()
        mock_server.name = "weather_server"
        
        tool = MCPTool(
            name="get_weather",
            description="Get weather information",
            server=mock_server,
            tool_name="get_weather",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        )
        
        assert tool.name == "get_weather"
        assert tool.description == "Get weather information"
        assert tool.server == mock_server
        assert tool.tool_name == "get_weather"

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self):
        """Test executing an MCP tool."""
        mock_server = Mock()
        mock_server.name = "weather_server"
        mock_server.connected = True
        
        # Mock MCP tool response
        mock_response = Mock()
        mock_response.content = [
            Mock(type="text", text='{"temperature": 72, "condition": "sunny"}')
        ]
        mock_server.call_tool = AsyncMock(return_value=mock_response)
        
        tool = MCPTool(
            name="get_weather",
            description="Get weather information",
            server=mock_server,
            tool_name="get_weather"
        )
        
        result = await tool.execute_async({"city": "San Francisco"})
        
        # Verify server was called correctly
        mock_server.call_tool.assert_called_once_with(
            "get_weather",
            {"city": "San Francisco"}
        )
        
        # Should return formatted result
        assert result is not None

    @pytest.mark.asyncio
    async def test_mcp_tool_server_not_connected(self):
        """Test MCP tool when server is not connected."""
        mock_server = Mock()
        mock_server.name = "disconnected_server"
        mock_server.connected = False
        
        tool = MCPTool(
            name="failing_tool",
            description="Tool on disconnected server",
            server=mock_server,
            tool_name="failing_tool"
        )
        
        with pytest.raises(RuntimeError, match="not connected"):
            await tool.execute_async({"param": "value"})

    @pytest.mark.asyncio
    async def test_mcp_tool_server_error(self):
        """Test MCP tool when server returns error."""
        mock_server = Mock()
        mock_server.name = "error_server"
        mock_server.connected = True
        mock_server.call_tool = AsyncMock(side_effect=Exception("Server error"))
        
        tool = MCPTool(
            name="error_tool",
            description="Tool that causes server error",
            server=mock_server,
            tool_name="error_tool"
        )
        
        with pytest.raises(Exception, match="Server error"):
            await tool.execute_async({"param": "value"})

    def test_mcp_tool_string_representation(self):
        """Test MCP tool string representation."""
        mock_server = Mock()
        mock_server.name = "test_server"
        
        tool = MCPTool(
            name="test_tool",
            description="Test MCP tool",
            server=mock_server,
            tool_name="test_tool"
        )
        
        str_repr = str(tool)
        assert "test_tool" in str_repr
        assert "test_server" in str_repr


class TestToolIntegration:
    """Test tool integration scenarios."""

    def test_mixed_tool_registry(self):
        """Test registry with both function and MCP tools."""
        registry = ToolRegistry()
        
        # Add function tool
        def local_function(text: str) -> str:
            return f"Local: {text}"
        
        function_tool = ToolDefinition(
            name="local_tool",
            description="Local function tool",
            function=local_function
        )
        
        # Add MCP tool
        mock_server = Mock()
        mock_server.name = "remote_server"
        
        mcp_tool = MCPTool(
            name="remote_tool",
            description="Remote MCP tool",
            server=mock_server,
            tool_name="remote_tool"
        )
        
        registry.register_tool(function_tool)
        registry.register_tool(mcp_tool)
        
        assert len(registry.tools) == 2
        assert "local_tool" in registry.tools
        assert "remote_tool" in registry.tools
        
        # Verify types
        assert isinstance(registry.tools["local_tool"], ToolDefinition)
        assert isinstance(registry.tools["remote_tool"], MCPTool)

    @pytest.mark.asyncio
    async def test_tool_execution_workflow(self):
        """Test complete tool execution workflow."""
        registry = ToolRegistry()
        
        # Register tools
        def calculator(a: int, b: int, operation: str = "add") -> int:
            operations = {
                "add": lambda x, y: x + y,
                "subtract": lambda x, y: x - y,
                "multiply": lambda x, y: x * y
            }
            return operations.get(operation, operations["add"])(a, b)
        
        calc_tool = ToolDefinition(
            name="calculator",
            description="Basic calculator",
            function=calculator,
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply"]}
                },
                "required": ["a", "b"]
            }
        )
        
        registry.register_tool(calc_tool)
        
        # Test tool discovery
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "calculator"
        
        # Test tool execution
        calc_tool_retrieved = registry.get_tool("calculator")
        result = calc_tool_retrieved.function(5, 3, "multiply")
        assert result == 15

    def test_tool_parameter_schema_validation(self):
        """Test tool parameter schema validation."""
        def weather_function(
            city: str,
            country: str = "US",
            units: str = "metric",
            include_forecast: bool = False
        ) -> Dict[str, Any]:
            return {
                "city": city,
                "country": country,
                "units": units,
                "forecast": include_forecast,
                "temperature": 22
            }
        
        weather_tool = ToolDefinition(
            name="get_weather",
            description="Get weather information for a city",
            function=weather_function,
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country code (default: US)",
                        "default": "US"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature units",
                        "default": "metric"
                    },
                    "include_forecast": {
                        "type": "boolean",
                        "description": "Include forecast data",
                        "default": False
                    }
                },
                "required": ["city"]
            }
        )
        
        # Verify the tool schema
        assert weather_tool.parameters["type"] == "object"
        assert "city" in weather_tool.parameters["required"]
        assert len(weather_tool.parameters["properties"]) == 4
        
        # Test function execution
        result = weather_tool.function("Paris", "FR", "metric", True)
        assert result["city"] == "Paris"
        assert result["country"] == "FR"
        assert result["forecast"] is True

    @pytest.mark.asyncio
    async def test_tool_error_propagation(self):
        """Test error propagation in tool execution."""
        def error_function(error_type: str) -> str:
            if error_type == "value":
                raise ValueError("Value error occurred")
            elif error_type == "type":
                raise TypeError("Type error occurred")
            elif error_type == "runtime":
                raise RuntimeError("Runtime error occurred")
            return "success"
        
        # Use ToolDefinition instead of FunctionTool
        error_tool = ToolDefinition(
            name="error_tool",
            description="Tool that can raise various errors",
            function=error_function
        )
        
        # Test different error types using ToolRegistry
        registry = ToolRegistry()
        registry.register_tool(error_tool)
        
        with pytest.raises(ValueError):
            await registry.execute_tool("error_tool", {"error_type": "value"})
        
        with pytest.raises(TypeError):
            await registry.execute_tool("error_tool", {"error_type": "type"})
        
        with pytest.raises(RuntimeError):
            await registry.execute_tool("error_tool", {"error_type": "runtime"})
        
        # Test successful execution
        result = await registry.execute_tool("error_tool", {"error_type": "none"})
        assert result == "success"

    def test_tool_discovery_from_multiple_sources(self):
        """Test tool discovery from both function and MCP sources."""
        registry = ToolRegistry()
        
        # Function tools
        def tool1():
            return "function_tool_1"
        
        def tool2():
            return "function_tool_2"
        
        # MCP tools (mocked)
        mock_server = Mock()
        mock_server.name = "mcp_server"
        
        # Register function tools
        registry.register_tool(ToolDefinition(
            name="func_tool_1",
            description="Function tool 1",
            function=tool1
        ))
        
        registry.register_tool(ToolDefinition(
            name="func_tool_2", 
            description="Function tool 2",
            function=tool2
        ))
        
        # Register MCP tools
        mcp_tool1 = MCPTool(
            name="mcp_tool_1",
            description="MCP tool 1",
            server=mock_server,
            tool_name="mcp_tool_1"
        )
        
        mcp_tool2 = MCPTool(
            name="mcp_tool_2",
            description="MCP tool 2", 
            server=mock_server,
            tool_name="mcp_tool_2"
        )
        
        registry.register_tool(mcp_tool1)
        registry.register_tool(mcp_tool2)
        
        # Verify all tools are registered
        all_tools = registry.list_tools()
        assert len(all_tools) == 4
        
        tool_names = [tool.name for tool in all_tools]
        assert "func_tool_1" in tool_names
        assert "func_tool_2" in tool_names
        assert "mcp_tool_1" in tool_names
        assert "mcp_tool_2" in tool_names
