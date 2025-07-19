# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Azure Functions Agent Package

Core agent framework for building intelligent Azure Functions with AI capabilities.
"""

from .agents import Agent, ReflectionAgent
from .core import AgentFunctionApp
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
from .runner import Runner
from .types import (
    AgentCapabilities,
    AgentCard,
    AgentMode,
    AgentProvider,
    AgentSkill,
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MCPConfig,
    ToolDefinition,
    TriggerType,
)

# Optional streaming support
try:
    from .streaming import AgentStreamingResponse, create_agent_stream
except ImportError:
    # Create dummy classes when streaming is not available
    class AgentStreamingResponse:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "Streaming requires azurefunctions-extensions-http-fastapi"
            )

    def create_agent_stream(*args, **kwargs):
        raise ImportError("Streaming requires azurefunctions-extensions-http-fastapi")


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
    "MCPConfig",
    "ToolDefinition",
    "ChatMessage",
    # A2A Types
    "AgentCapabilities",
    "AgentCard",
    "AgentProvider",
    "AgentSkill",
    # Handoff System
    "HandoffConfig",
    "HandoffMode",
    "HandoffStrategy",
    "HandoffTarget",
    "HandoffRequest",
    "HandoffResult",
    "AgentResponse",
    "ControlReturn",
    "ControlFlowManager",
    "HandoffEngine",
    # MCP Integration
    "MCPServer",
    "MCPServerMode",
    "MCPServerSseParams",
    "MCPServerStdioParams",
    "MCPServerStreamableHttpParams",
    "MCPUtil",
    # Streaming (optional)
    "AgentStreamingResponse",
    "create_agent_stream",
]

__version__ = "0.0.1a19"
__author__ = "Microsoft Azure Functions Team"
__license__ = "MIT"
