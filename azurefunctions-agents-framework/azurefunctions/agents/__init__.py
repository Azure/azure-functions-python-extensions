# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure Functions Agent Package

Core agent framework for building intelligent Azure Functions with AI capabilities.
"""

from .agents import Agent, ReflectionAgent
from .core import AgentFunctionApp
from .runner import Runner
from .handoff import (
    AgentResponse,
    ControlFlowManager,
    ControlReturn,
    HandoffConfig,
    HandoffEngine,
    HandoffMode,
    HandoffRequest,
    HandoffResult,
    HandoffStrategy,
    HandoffTarget,
)
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
    # Core Framework
    "Agent",
    "AgentFunctionApp", 
    "ReflectionAgent",
    "Runner",
    "AgentMode",
    "TriggerType",
    "LLMConfig",
    "LLMProvider",
    "ToolDefinition",
    "ChatMessage",
    
    # Multi-Agent Handoff System
    "HandoffMode",
    "HandoffStrategy", 
    "ControlReturn",
    "HandoffTarget",
    "HandoffConfig",
    "HandoffRequest",
    "HandoffResult",
    "AgentResponse",
    "ControlFlowManager",
    "HandoffEngine",
    
    # MCP Integration
    "MCPConfig",
    "MCPServer",
    "MCPServerMode",
    "MCPServerStdioParams",
    "MCPServerSseParams",
    "MCPServerStreamableHttpParams",
    "MCPUtil",
]

__version__ = "0.0.1a3"
__author__ = "Microsoft Azure Functions Team"
__license__ = "MIT"
