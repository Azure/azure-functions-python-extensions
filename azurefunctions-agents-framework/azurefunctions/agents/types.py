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


class MCPServerMode(Enum):
    """MCP Server communication modes."""

    STDIO = "stdio"  # Standard input/output communication
    SSE = "sse"  # Server-sent events
    STREAMABLE_HTTP = "streamable_http"  # Streamable HTTP communication


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


# Abstract Request and Response classes for clean separation of concerns


class Request(abc.ABC):
    """Abstract base class for all agent requests."""

    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary format for agent processing."""
        pass


class Response(abc.ABC):
    """Abstract base class for all agent responses."""

    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        pass


@dataclass
class ChatRequest(Request):
    """
    Concrete request class for chat-based agent interactions.
    Provides a clean API for building agent requests.
    """

    message: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    context: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for agent processing."""
        result = {}
        if self.message:
            result["message"] = self.message
        if self.messages:
            result["messages"] = self.messages
        if self.context:
            result["context"] = self.context
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.user_id:
            result["user_id"] = self.user_id
        if self.session_id:
            result["session_id"] = self.session_id
        return result


@dataclass
class ChatResponse(Response):
    """
    Concrete response class for chat-based agent interactions.
    Contains the agent's response and metadata.
    """

    response: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None
    context: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        result = {"status": self.status}
        if self.response:
            result["response"] = self.response
        if self.messages:
            result["messages"] = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                    **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                    **({"name": msg.name} if msg.name else {}),
                }
                for msg in self.messages
            ]
        if self.context:
            result["context"] = self.context
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.metadata:
            result["metadata"] = self.metadata
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class MessageRequest:
    """
    DEPRECATED: Use ChatRequest instead.
    Structured request object that users can create and pass to the runner.
    Provides a clean API for building agent requests.
    """

    message: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    context: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for agent processing."""
        result = {}
        if self.message:
            result["message"] = self.message
        if self.messages:
            result["messages"] = self.messages
        if self.context:
            result["context"] = self.context
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result
