# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure Functions Agent Package

Core agent framework for building intelligent Azure Functions with AI capabilities.
"""

from .core import Agent, AgentFunctionApp, ReflectionAgent
from .mcp import (
    MCPServer,
    MCPServerSse,
    MCPServerStdio,
    MCPServerStreamableHttp,
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
    "MCPServerSse",
    "MCPServerStdio",
    "MCPServerStreamableHttp",
    "MCPUtil",
]

__version__ = "0.0.1a1"
__author__ = "Microsoft Azure Functions Team"
__license__ = "MIT"
