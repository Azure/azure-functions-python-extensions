# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure Functions Agent Package

Core agent framework for building intelligent Azure Functions with AI capabilities.
"""

from .agents import Agent, ReflectionAgent
from .core import AgentFunctionApp
from .mcp import (
    MCPServer,
    MCPServerMode,
    MCPServerSseParams,
    MCPServerStdioParams,
    MCPServerStreamableHttpParams,
    MCPUtil,
)
from .types import (
    AgentMode,
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MCPConfig,
    ToolDefinition,
    TriggerType,
)

__all__ = [
    "Agent",
    "AgentFunctionApp",
    "ReflectionAgent",
    "AgentMode",
    "TriggerType",
    "LLMConfig",
    "LLMProvider",
    "ToolDefinition",
    "ChatMessage",
    "MCPConfig",
    "MCPServer",
    "MCPServerMode",
    "MCPServerStdioParams",
    "MCPServerSseParams",
    "MCPServerStreamableHttpParams",
    "MCPUtil",
]

__version__ = "0.0.1a2"
__author__ = "Microsoft Azure Functions Team"
__license__ = "MIT"
