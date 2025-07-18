# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tool registry - unified interface for both MCP and function tools."""

import logging
from typing import Any, Dict, List, Optional

from ..types import MCPConfig, ToolFunction
from .function_tools import FunctionToolManager
from .mcp_tools import MCPToolManager


class ToolRegistry:
    """
    Unified tool registry that manages both MCP and function-based tools.

    Provides a single interface for:
    - Tool registration and discovery
    - Tool execution
    - Schema generation
    """

    def __init__(self, mcp_config: Optional[MCPConfig] = None, mcp_tool_executor=None):
        """
        Initialize the tool registry.

        Args:
            mcp_config: Optional MCP configuration
            mcp_tool_executor: Optional callback for executing MCP tools registered by agents
        """
        self.logger = logging.getLogger("ToolRegistry")

        # Initialize tool managers
        self.function_manager = FunctionToolManager()
        self.mcp_manager = (
            MCPToolManager(mcp_config or MCPConfig()) if mcp_config else None
        )

        # Storage for MCP tools registered directly by agents
        self._mcp_tools_registry: Dict[str, Dict[str, Any]] = {}

        # Callback for executing MCP tools registered by agents
        self._mcp_tool_executor = mcp_tool_executor

    # Function tool methods
    def register_function_tool(
        self,
        name: str,
        function: ToolFunction,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        required_params: Optional[List[str]] = None,
    ) -> bool:
        """Register a function-based tool."""
        return self.function_manager.register_tool(
            name, function, description, parameters, required_params
        )

    def unregister_function_tool(self, name: str) -> bool:
        """Unregister a function-based tool."""
        return self.function_manager.unregister_tool(name)

    # MCP tool methods
    async def add_mcp_server(self, server) -> bool:
        """Add an MCP server and discover its tools."""
        if not self.mcp_manager:
            self.logger.warning("MCP manager not initialized")
            return False

        return await self.mcp_manager.add_server(server)

    async def remove_mcp_server(self, server_name: str) -> bool:
        """Remove an MCP server and its tools."""
        if not self.mcp_manager:
            self.logger.warning("MCP manager not initialized")
            return False

        return await self.mcp_manager.remove_server(server_name)

    def register_mcp_tool(self, server, tool):
        """Register an MCP tool from a server."""
        # Store the tool in our registry regardless of whether MCP manager is initialized
        tool_info = {
            "name": tool.name,
            "description": tool.description,
            "type": "mcp",
            "server": server.name,
            "parameters": getattr(tool, "inputSchema", {}).get("properties", {}),
            "required_params": getattr(tool, "inputSchema", {}).get("required", []),
        }

        self._mcp_tools_registry[tool.name] = tool_info
        self.logger.debug(
            f"Registered MCP tool '{tool.name}' from server '{server.name}'"
        )
        return True

    # Unified tool interface
    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool (either function or MCP).

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        # Check MCP tools registered directly by agents first
        if tool_name in self._mcp_tools_registry:
            if self._mcp_tool_executor:
                return await self._mcp_tool_executor(tool_name, arguments)
            else:
                return {
                    "error": f"No executor available for MCP tool '{tool_name}'",
                    "status": "error",
                }

        # Check MCP tools from manager
        if self.mcp_manager and tool_name in self.mcp_manager.available_tools:
            return await self.mcp_manager.execute_tool(tool_name, arguments)

        # Otherwise, try function tools
        return await self.function_manager.execute_tool(tool_name, arguments)

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools (both function and MCP).

        Returns:
            List of tool information dictionaries
        """
        tools = []

        # Add function tools
        tools.extend(self.function_manager.list_tools())

        # Add MCP tools from manager (if available)
        if self.mcp_manager:
            tools.extend(self.mcp_manager.list_tools())

        # Add MCP tools registered directly by agents
        tools.extend(list(self._mcp_tools_registry.values()))

        return tools

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema dictionary if found, None otherwise
        """
        # Check MCP tools registered directly by agents first
        if tool_name in self._mcp_tools_registry:
            tool_info = self._mcp_tools_registry[tool_name]
            return {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": tool_info.get("parameters", {}),
                        "required": tool_info.get("required_params", []),
                    },
                },
            }

        # Check MCP tools from manager
        if self.mcp_manager and tool_name in self.mcp_manager.available_tools:
            return self.mcp_manager.get_tool_schema(tool_name)

        # Check function tools
        return self.function_manager.get_tool_schema(tool_name)

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get all tools formatted for LLM function calling.

        Returns:
            List of tool schemas for LLM
        """
        tools_schema = []

        # Get all tools
        all_tools = self.list_all_tools()

        for tool_info in all_tools:
            tool_name = tool_info["name"]
            schema = self.get_tool_schema(tool_name)

            if schema:
                tools_schema.append(schema)

        return tools_schema

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool exists.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool exists, False otherwise
        """
        # Check MCP tools from manager or registered directly by agents
        if self.mcp_manager and (
            tool_name in self.mcp_manager.available_tools
            or tool_name in self._mcp_tools_registry
        ):
            return True

        # Check function tools
        return tool_name in self.function_manager.tools

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information dictionary if found, None otherwise
        """
        all_tools = self.list_all_tools()

        for tool_info in all_tools:
            if tool_info["name"] == tool_name:
                return tool_info

        return None

    async def refresh_tools(self) -> bool:
        """
        Refresh all tools (mainly for MCP tools).

        Returns:
            True if refresh was successful, False otherwise
        """
        if self.mcp_manager:
            return await self.mcp_manager.refresh_tools()

        return True

    async def cleanup(self):
        """Clean up all tool managers."""
        self.logger.info("Cleaning up tool registry")

        if self.mcp_manager:
            await self.mcp_manager.cleanup()

        # Function tools don't need cleanup
        self.logger.info("Tool registry cleanup complete")
