# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Shared utilities for formatting MCP tool results."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MCPResultFormatter:
    """Utility class for formatting MCP tool results consistently across the framework."""

    @staticmethod
    def format_tool_result(result: Any) -> Dict[str, Any]:
        """
        Convert MCP tool result to our framework's standard format.

        Args:
            result: Raw MCP tool result

        Returns:
            Formatted result dictionary with 'result' and 'status' keys
        """
        try:
            # The MCP tool result is typically a CallToolResult with content
            if hasattr(result, "content") and result.content:
                if len(result.content) == 1:
                    # Single content item
                    content = result.content[0]
                    if hasattr(content, "text"):
                        return {"result": content.text, "status": "success"}
                    else:
                        return {"result": str(content), "status": "success"}
                else:
                    # Multiple content items - join them
                    contents = []
                    for item in result.content:
                        if hasattr(item, "text"):
                            contents.append(item.text)
                        else:
                            contents.append(str(item))
                    return {"result": "\n".join(contents), "status": "success"}
            else:
                return {"result": str(result), "status": "success"}

        except Exception as e:
            logger.error(f"Error formatting MCP result: {e}")
            return {"result": str(result), "status": "success"}

    @staticmethod
    def format_tool_result_as_string(result: Any) -> str:
        """
        Convert MCP tool result to a string representation.

        Args:
            result: Raw MCP tool result

        Returns:
            String representation of the result
        """
        try:
            if hasattr(result, "content") and result.content:
                if len(result.content) == 1:
                    content_item = result.content[0]
                    if hasattr(content_item, "text"):
                        return content_item.text
                    else:
                        return str(content_item)
                elif len(result.content) > 1:
                    # Multiple content items - join them
                    contents = []
                    for item in result.content:
                        if hasattr(item, "text"):
                            contents.append(item.text)
                        else:
                            contents.append(str(item))
                    return "\n".join(contents)
                else:
                    logger.error(f"Empty MCP tool result: {result}")
                    return "Tool completed but returned no content."
            else:
                logger.error(f"Unexpected MCP tool result format: {result}")
                return str(result)

        except Exception as e:
            logger.error(f"Error formatting MCP result as string: {e}")
            return str(result)
