# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Function-based tools manager."""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from ..types import ToolDefinition, ToolFunction


class FunctionToolManager:
    """
    Manages function-based tools for the agent.

    Handles:
    - Function tool registration
    - Tool execution
    - Schema generation from function signatures
    """

    def __init__(self):
        """Initialize the function tool manager."""
        self.logger = logging.getLogger("FunctionToolManager")
        self.tools: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        function: ToolFunction,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        required_params: Optional[List[str]] = None,
    ) -> bool:
        """
        Register a function as a tool.

        Args:
            name: Name of the tool
            function: Function to register
            description: Description of the tool
            parameters: Parameter schema
            required_params: List of required parameter names

        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Use function docstring as description if not provided
            if not description:
                description = function.__doc__ or f"Tool: {name}"

            # Auto-generate parameters schema if not provided
            if not parameters:
                parameters = self._generate_parameters_schema(function)

            # Auto-detect required parameters if not provided
            if not required_params:
                required_params = self._get_required_parameters(function)

            tool_def = ToolDefinition(
                name=name,
                description=description,
                function=function,
                parameters=parameters,
                required_params=required_params,
            )

            self.tools[name] = tool_def
            self.logger.info(f"Registered function tool: {name}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to register tool {name}: {e}")
            return False

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Name of the tool to unregister

        Returns:
            True if unregistration was successful, False otherwise
        """
        if name in self.tools:
            del self.tools[name]
            self.logger.info(f"Unregistered function tool: {name}")
            return True
        else:
            self.logger.warning(f"Tool {name} not found for unregistration")
            return False

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a function tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the function

        Returns:
            Tool execution result
        """
        try:
            if tool_name not in self.tools:
                return {
                    "error": f"Function tool '{tool_name}' not found",
                    "status": "error",
                }

            tool = self.tools[tool_name]

            self.logger.info(f"Executing function tool: {tool_name}")

            # Execute the function
            result = tool.function(**arguments)

            # Handle async functions
            if asyncio.iscoroutine(result):
                result = await result

            return {"result": result, "status": "success"}

        except Exception as e:
            self.logger.error(f"Function tool execution failed for {tool_name}: {e}")
            return {"error": str(e), "status": "error"}

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered function tools.

        Returns:
            List of tool information dictionaries
        """
        tools = []

        for tool_name, tool_def in self.tools.items():
            tool_info = {
                "name": tool_name,
                "description": tool_def.description,
                "parameters": tool_def.parameters,
                "required_params": tool_def.required_params,
                "type": "function",
            }

            tools.append(tool_info)

        return tools

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.

        Args:
            name: Name of the tool

        Returns:
            ToolDefinition if found, None otherwise
        """
        return self.tools.get(name)

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a specific function tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool schema dictionary if found, None otherwise
        """
        if tool_name not in self.tools:
            return None

        tool = self.tools[tool_name]

        schema = {
            "type": "function",
            "function": {"name": tool_name, "description": tool.description},
        }

        # Add parameters if available
        if tool.parameters:
            schema["function"]["parameters"] = {
                "type": "object",
                "properties": tool.parameters,
                "required": tool.required_params or [],
            }

        return schema

    def _generate_parameters_schema(
        self, function: Callable
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a parameters schema from a function signature.

        Args:
            function: Function to analyze

        Returns:
            Parameters schema dictionary
        """
        try:
            sig = inspect.signature(function)
            parameters = {}

            for param_name, param in sig.parameters.items():
                param_info = {"type": "string"}  # Default type

                # Try to infer type from annotation
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_info["type"] = "integer"
                    elif param.annotation == float:
                        param_info["type"] = "number"
                    elif param.annotation == bool:
                        param_info["type"] = "boolean"
                    elif param.annotation == list:
                        param_info["type"] = "array"
                    elif param.annotation == dict:
                        param_info["type"] = "object"

                # Add default value if available
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters[param_name] = param_info

            return parameters if parameters else None

        except Exception as e:
            self.logger.warning(
                f"Failed to generate parameters schema for function: {e}"
            )
            return None

    def _get_required_parameters(self, function: Callable) -> List[str]:
        """
        Get required parameters from a function signature.

        Args:
            function: Function to analyze

        Returns:
            List of required parameter names
        """
        try:
            sig = inspect.signature(function)
            required_params = []

            for param_name, param in sig.parameters.items():
                if param.default == inspect.Parameter.empty:
                    required_params.append(param_name)

            return required_params

        except Exception as e:
            self.logger.warning(f"Failed to get required parameters for function: {e}")
            return []
