# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""MCP (Model Context Protocol) tools manager."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from mcp import Tool as MCPTool
from mcp.types import CallToolResult

from ..mcp.result_formatter import MCPResultFormatter
from ..types import MCPConfig


class MCPToolManager:
    """
    Manages MCP (Model Context Protocol) tools and servers.

    Handles:
    - MCP server connections
    - Tool discovery from MCP servers
    - Tool execution via MCP
    - Server lifecycle management
    """

    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP tool manager.

        Args:
            config: MCP configuration
        """
        self.config = config
        self.logger = logging.getLogger("MCPToolManager")
        self.servers: Dict[str, Any] = {}  # Store MCPServer instances
        self.available_tools: Dict[str, MCPTool] = {}

    @staticmethod
    def _sanitize_tool_name(name: str) -> str:
        """
        Sanitize tool name to match OpenAI's function name requirements.

        OpenAI requires function names to match the pattern: ^[a-zA-Z0-9_-]+$
        This means only alphanumeric characters, underscores, and hyphens are allowed.

        Args:
            name: Original tool name

        Returns:
            Sanitized tool name that matches OpenAI's requirements
        """
        # Replace any character that's not alphanumeric, underscore, or hyphen with underscore
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure it starts with a letter or underscore (OpenAI best practice)
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != "_":
            sanitized = f"_{sanitized}"

        return sanitized

    async def add_server(self, server) -> bool:
        """
        Add and connect to an MCP server.

        Args:
            server: MCPServer instance to add

        Returns:
            True if server was added successfully, False otherwise
        """
        try:
            self.logger.info(f"Adding MCP server: {server.name}")

            # Connect to the server (server handles its own connection logic)
            await server.connect()

            # Store the server
            self.servers[server.name] = server

            # List available tools from the server
            tools = await server.list_tools()

            # Register tools from this server
            for tool in tools:
                # Create sanitized tool name for OpenAI compatibility
                sanitized_server_name = self._sanitize_tool_name(server.name)
                sanitized_tool_name = self._sanitize_tool_name(tool.name)
                tool_key = f"{sanitized_server_name}-{sanitized_tool_name}"

                # Store with original server and tool names for execution
                tool._original_server_name = server.name
                tool._original_tool_name = tool.name
                tool._sanitized_name = tool_key

                self.available_tools[tool_key] = tool
                self.logger.info(
                    f"Registered MCP tool: {tool_key} (original: {server.name}-{tool.name})"
                )

            self.logger.info(f"Successfully added MCP server: {server.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add MCP server {server.name}: {e}")
            return False

    async def remove_server(self, server_name: str) -> bool:
        """
        Remove an MCP server and clean up its tools.

        Args:
            server_name: Name of the server to remove

        Returns:
            True if server was removed successfully, False otherwise
        """
        try:
            if server_name not in self.servers:
                self.logger.warning(f"MCP server {server_name} not found")
                return False

            server = self.servers[server_name]

            # Clean up server
            await server.cleanup()

            # Remove server and its tools
            del self.servers[server_name]

            # Remove tools from this server
            sanitized_server_name = self._sanitize_tool_name(server_name)
            tools_to_remove = [
                tool_key
                for tool_key in self.available_tools.keys()
                if tool_key.startswith(f"{sanitized_server_name}-")
            ]

            for tool_key in tools_to_remove:
                del self.available_tools[tool_key]
                self.logger.info(f"Removed MCP tool: {tool_key}")

            self.logger.info(f"Removed MCP server: {server_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove MCP server {server_name}: {e}")
            return False

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool.

        Args:
            tool_name: Name of the tool (format: "server_name:tool_name")
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        try:
            if tool_name not in self.available_tools:
                return {"error": f"MCP tool '{tool_name}' not found", "status": "error"}

            # Get the tool to access original server and tool names
            tool = self.available_tools[tool_name]
            original_server_name = getattr(tool, "_original_server_name", None)
            original_tool_name = getattr(tool, "_original_tool_name", None)

            # Fall back to parsing sanitized name if original names not available
            if not original_server_name or not original_tool_name:
                # Extract server name from sanitized tool name
                parts = tool_name.split("-", 1)
                if len(parts) != 2:
                    return {
                        "error": f"Invalid MCP tool name format: {tool_name}",
                        "status": "error",
                    }

                # Try to find the server by checking all server names
                original_server_name = None
                for server_name in self.servers.keys():
                    if self._sanitize_tool_name(server_name) == parts[0]:
                        original_server_name = server_name
                        break

                if not original_server_name:
                    return {
                        "error": f"MCP server for tool '{tool_name}' not found",
                        "status": "error",
                    }

                # The tool name is the second part (already sanitized, but we need the original)
                original_tool_name = parts[
                    1
                ]  # This might be sanitized, but should work for execution

            if original_server_name not in self.servers:
                return {
                    "error": f"MCP server '{original_server_name}' not available",
                    "status": "error",
                }

            server = self.servers[original_server_name]

            self.logger.info(
                f"Executing MCP tool: {tool_name} (original: {original_server_name}-{original_tool_name})"
            )

            # Execute the tool using the server's call_tool method with original tool name
            result = await server.call_tool(original_tool_name, arguments)

            # Convert result to our standard format using shared formatter
            return MCPResultFormatter.format_tool_result(result)

        except Exception as e:
            self.logger.error(f"MCP tool execution failed for {tool_name}: {e}")
            return {"error": str(e), "status": "error"}

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available MCP tools.

        Returns:
            List of tool information dictionaries
        """
        tools = []

        for tool_key, tool in self.available_tools.items():
            server_name = tool_key.split("-", 1)[0]

            tool_info = {
                "name": tool_key,
                "server": server_name,
                "description": tool.description,
                "type": "mcp",
            }

            # Add input schema if available
            if hasattr(tool, "inputSchema") and tool.inputSchema:
                tool_info["parameters"] = tool.inputSchema

            tools.append(tool_info)

        return tools

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a specific MCP tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema dictionary if found, None otherwise
        """
        if tool_name not in self.available_tools:
            return None

        tool = self.available_tools[tool_name]

        schema = {
            "type": "function",
            "function": {"name": tool_name, "description": tool.description},
        }

        # Add parameters if available
        if hasattr(tool, "inputSchema") and tool.inputSchema:
            schema["function"]["parameters"] = tool.inputSchema

        return schema

    async def refresh_tools(self) -> bool:
        """
        Refresh tools from all connected MCP servers.

        Returns:
            True if refresh was successful, False otherwise
        """
        try:
            self.logger.info("Refreshing MCP tools")

            # Clear existing tools
            self.available_tools.clear()

            # Re-discover tools from each server
            for server_name, server in self.servers.items():
                try:
                    tools = await server.list_tools()

                    for tool in tools:
                        tool_key = f"{server_name}:{tool.name}"
                        self.available_tools[tool_key] = tool

                except Exception as e:
                    self.logger.error(
                        f"Failed to refresh tools from {server_name}: {e}"
                    )

            self.logger.info(f"Refreshed {len(self.available_tools)} MCP tools")
            return True

        except Exception as e:
            self.logger.error(f"Failed to refresh MCP tools: {e}")
            return False

    async def cleanup(self):
        """Clean up all MCP servers and connections."""
        self.logger.info("Cleaning up MCP tool manager")

        for server_name in list(self.servers.keys()):
            await self.remove_server(server_name)

        self.available_tools.clear()
        self.servers.clear()
