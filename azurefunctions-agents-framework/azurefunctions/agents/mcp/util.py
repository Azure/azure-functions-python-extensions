# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Utility functions for MCP integration with Azure Functions Agent Framework.

Based on the OpenAI agents SDK MCP utilities but adapted for our framework.
"""

import functools
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .result_formatter import MCPResultFormatter

if TYPE_CHECKING:
    from mcp.types import Tool as MCPTool

    from .server import MCPServer

# Setup logger
logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class ModelBehaviorError(AgentError):
    """Error raised due to unexpected model behavior."""

    pass


class UserError(AgentError):
    """Error raised due to user configuration or input issues."""

    pass


class MCPTool:
    """Represents an MCP tool for the Azure Functions framework."""

    def __init__(
        self,
        name: str,
        description: str,
        server: "MCPServer",
        mcp_tool: "MCPTool",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.server = server
        self.mcp_tool = mcp_tool
        self.parameters_schema = parameters_schema or {}

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MCP tool with the given arguments."""
        try:
            result = await self.server.call_tool(self.name, arguments)
            return MCPResultFormatter.format_tool_result(result)
        except Exception as e:
            logger.error(f"Error executing MCP tool {self.name}: {e}")
            return {"error": str(e), "status": "error"}


class MCPUtil:
    """Set of utilities for interop between MCP and Azure Functions Agent Framework."""

    @classmethod
    async def get_all_function_tools(
        cls, servers: List["MCPServer"], convert_schemas_to_strict: bool = False
    ) -> List[MCPTool]:
        """Get all function tools from a list of MCP servers."""
        tools = []
        tool_names: set[str] = set()

        for server in servers:
            server_tools = await cls.get_function_tools(
                server, convert_schemas_to_strict
            )
            server_tool_names = {tool.name for tool in server_tools}

            if len(server_tool_names & tool_names) > 0:
                raise UserError(
                    f"Duplicate tool names found across MCP servers: "
                    f"{server_tool_names & tool_names}"
                )

            tool_names.update(server_tool_names)
            tools.extend(server_tools)

        return tools

    @classmethod
    async def get_function_tools(
        cls, server: "MCPServer", convert_schemas_to_strict: bool = False
    ) -> List[MCPTool]:
        """Get all function tools from a single MCP server."""
        logger.info(f"Fetching tools from MCP server: {server.name}")

        try:
            mcp_tools = await server.list_tools()
            logger.info(f"Found {len(mcp_tools)} tools from server {server.name}")

            tools = []
            for mcp_tool in mcp_tools:
                tool = cls.to_function_tool(mcp_tool, server, convert_schemas_to_strict)
                tools.append(tool)

            return tools

        except Exception as e:
            logger.error(f"Error fetching tools from MCP server {server.name}: {e}")
            raise

    @classmethod
    def to_function_tool(
        cls,
        tool: "MCPTool",
        server: "MCPServer",
        convert_schemas_to_strict: bool = False,
    ) -> MCPTool:
        """Convert an MCP tool to an Azure Functions framework tool."""

        # Extract schema information
        schema = getattr(tool, "inputSchema", {})
        if not schema:
            schema = {"type": "object", "properties": {}}

        # MCP spec doesn't require the inputSchema to have `properties`, but our framework expects it.
        if "properties" not in schema:
            schema["properties"] = {}

        # TODO: Add strict schema conversion if needed
        # if convert_schemas_to_strict:
        #     try:
        #         schema = ensure_strict_json_schema(schema)
        #     except Exception as e:
        #         logger.info(f"Error converting MCP schema to strict mode: {e}")

        return MCPTool(
            name=tool.name,
            description=tool.description or f"MCP tool: {tool.name}",
            server=server,
            mcp_tool=tool,
            parameters_schema=schema,
        )

    @classmethod
    async def invoke_mcp_tool(
        cls, server: "MCPServer", tool: "MCPTool", input_json: str
    ) -> str:
        """Invoke an MCP tool and return the result as a string."""

        try:
            json_data: Dict[str, Any] = json.loads(input_json) if input_json else {}
        except Exception as e:
            logger.error(f"Invalid JSON input for tool {tool.name}: {input_json}")
            raise ModelBehaviorError(
                f"Invalid JSON input for tool {tool.name}: {input_json}"
            ) from e

        logger.debug(f"Invoking MCP tool {tool.name} with input {json_data}")

        try:
            result = await server.call_tool(tool.name, json_data)
        except Exception as e:
            logger.error(f"Error invoking MCP tool {tool.name}: {e}")
            raise AgentError(f"Error invoking MCP tool {tool.name}: {e}") from e

        logger.debug(f"MCP tool {tool.name} completed with result: {result}")

        # Convert the result to string format using shared formatter
        return MCPResultFormatter.format_tool_result_as_string(result)

    @classmethod
    def convert_mcp_tools_to_llm_schema(
        cls, mcp_tools: List[MCPTool]
    ) -> List[Dict[str, Any]]:
        """Convert MCP tools to LLM function calling schema."""
        llm_tools = []

        for tool in mcp_tools:
            llm_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            llm_tools.append(llm_tool)

        return llm_tools

    @classmethod
    async def cleanup_servers(cls, servers: List["MCPServer"]):
        """Cleanup all MCP servers."""
        for server in servers:
            try:
                await server.cleanup()
                logger.info(f"Cleaned up MCP server: {server.name}")
            except Exception as e:
                logger.error(f"Error cleaning up MCP server {server.name}: {e}")

    @classmethod
    async def connect_servers(cls, servers: List["MCPServer"]):
        """Connect to all MCP servers."""
        for server in servers:
            try:
                await server.connect()
                logger.info(f"Connected to MCP server: {server.name}")
            except Exception as e:
                logger.error(f"Error connecting to MCP server {server.name}: {e}")
                raise
