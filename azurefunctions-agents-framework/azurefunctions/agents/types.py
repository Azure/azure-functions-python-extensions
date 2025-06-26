# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Core types and data structures for the Azure Functions Agent framework."""

import abc
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# Type definitions
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")
MaybeAwaitable = Union[Awaitable[T], T]
ToolFunction = Callable[..., MaybeAwaitable[Any]]


class AgentMode(Enum):
    """Operating modes for the agent."""

    AZURE_FUNCTION_AGENT = "azure_function_agent"  # Standard Azure Function agent
    A2A = "a2a"  # Agent-to-Agent protocol compliant


class TriggerType(Enum):
    """Supported trigger types for agent functions."""

    HTTP_ROUTE = "http_route"
    TIMER = "timer"


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE_AI = "azure_ai"


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    max_retries: int = 3

    # Azure-specific settings
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None

    # Additional provider-specific settings
    extra_headers: Optional[Dict[str, str]] = None
    extra_body: Optional[Dict[str, Any]] = None


@dataclass
class ChatMessage:
    """Represents a chat message in a conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ToolDefinition:
    """Defines a tool that can be used by the agent."""

    name: str
    description: str
    function: ToolFunction
    parameters: Optional[Dict[str, Any]] = None
    required_params: Optional[List[str]] = None


@dataclass
class MCPConfig:
    """Configuration for MCP (Model Context Protocol) integration."""

    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3


# MCP Server types - forward reference to avoid circular imports
# The actual implementation is in the mcp module
MCPServer = Any  # Will be properly typed when importing from mcp module


# A2A Protocol types (using SDK types as aliases)
try:
    from a2a.types import AgentCapabilities
    from a2a.types import AgentCard as SDKAgentCard
    from a2a.types import AgentProvider, AgentSkill
    from a2a.types import Task as SDKTask
    from a2a.types import TaskState as SDKTaskState

    # Create aliases for backward compatibility
    TaskState = SDKTaskState
    AgentCard = SDKAgentCard
    Task = SDKTask

except ImportError:
    # Fallback definitions if a2a-sdk is not available
    class TaskState(Enum):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    @dataclass
    class AgentCard:
        name: str
        description: str
        version: str
        url: str

    @dataclass
    class Task:
        id: str
        state: TaskState
        input: Dict[str, Any]
        output: Optional[Dict[str, Any]] = None
        created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
        updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
        error: Optional[str] = None
