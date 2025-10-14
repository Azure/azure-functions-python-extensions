#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License.
from ..utils import _extract_type_and_description
from .mcp import MCPToolTrigger, MCPToolContext

import inspect
import json
from typing import Callable

from azure.functions import FunctionRegister, Blueprint, AuthLevel


# Map Python types to MCP property types
_TYPE_MAPPING = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
}

class McpApp(Blueprint, FunctionRegister):
    """
    MCP-specific app object.
    Extends FunctionRegister to reuse function registration and trigger infrastructure.
    """

    def __init__(self, auth_level=AuthLevel.ANONYMOUS):
        super().__init__(auth_level=auth_level)

    def mcp_tool(self) -> Callable[[Callable], Callable]:
        """
        Decorator to register an MCP tool function.

        Automatically:
        - Infers tool name from function name
        - Extracts first line of docstring as description
        - Extracts parameters and types for tool properties
        - Handles MCPToolContext injection
        """

        def decorator(target_func: Callable) -> Callable:
            # Extract function metadata
            sig = inspect.signature(target_func)
            tool_name = target_func.__name__
            description = (target_func.__doc__ or "").strip().split("\n")[0]

            # Build tool properties metadata
            tool_properties = []
            for param_name, param in sig.parameters.items():
                param_type_hint = param.annotation if param.annotation != inspect.Parameter.empty else str
                actual_type, param_description = _extract_type_and_description(param_name, param_type_hint)
                if actual_type is MCPToolContext:
                    continue  # context is injected, not a property
                property_type = _TYPE_MAPPING.get(actual_type, "string")
                tool_properties.append({
                    "propertyName": param_name,
                    "propertyType": property_type,
                    "description": param_description,
                })

            tool_properties_json = json.dumps(tool_properties)

            # Wrapper function for MCP trigger
            def wrapper(context: str) -> str:
                try:
                    content = json.loads(context)
                    arguments = content.get("arguments", {})
                    kwargs = {}

                    for param_name, param in sig.parameters.items():
                        param_type_hint = param.annotation if param.annotation != inspect.Parameter.empty else str
                        actual_type, _ = _extract_type_and_description(param_name, param_type_hint)

                        if actual_type is MCPToolContext:
                            kwargs[param_name] = content
                        elif param_name in arguments:
                            kwargs[param_name] = arguments[param_name]
                        else:
                            return f"Error: Missing required parameter '{param_name}' for '{tool_name}'"

                    result = target_func(**kwargs)
                    return str(result)

                except Exception as e:
                    return f"Error executing function '{tool_name}': {str(e)}"

            wrapper.__name__ = target_func.__name__
            wrapper.__doc__ = target_func.__doc__

            # Register as MCP trigger using existing azure-functions infrastructure
            fb = self._configure_function_builder(lambda fb: fb)(wrapper)
            fb.add_trigger(
                trigger=MCPToolTrigger(
                    name="context",
                    tool_name=tool_name,
                    description=description,
                    tool_properties=tool_properties_json
                )
            )

            return fb

        return decorator
