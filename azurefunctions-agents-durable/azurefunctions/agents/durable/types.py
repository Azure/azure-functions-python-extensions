"""Core types for the Durable Functions Agents framework."""

from enum import Enum
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass


class CallMode(Enum):
    """Supported agent call modes."""
    HTTP = "http"
    MCP = "mcp"
    A2A_TASK = "a2a_task"
    A2A_SYNC = "a2a_sync"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    call_mode: CallMode
    endpoint: Optional[str] = None
    auth_token: Optional[str] = None
    client_type: Optional[str] = None  # For MCP: "stdio" or "sse"
    extra_config: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create AgentConfig from dictionary."""
        call_mode = CallMode(data["call_mode"]) if isinstance(data["call_mode"], str) else data["call_mode"]
        return cls(
            name=data["name"],
            call_mode=call_mode,
            endpoint=data.get("endpoint"),
            auth_token=data.get("auth_token"),
            client_type=data.get("client_type"),
            extra_config=data.get("extra_config")
        )


@dataclass
class AgentCallRequest:
    """Request for calling an agent."""
    agent_name: str
    method: str
    args: Optional[Dict[str, Any]] = None
    kwargs: Optional[Dict[str, Any]] = None


@dataclass
class AgentCallResponse:
    """Response from calling an agent."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    
    @classmethod
    def success_response(cls, result: Any) -> "AgentCallResponse":
        """Create a successful response."""
        return cls(success=True, result=result)
    
    @classmethod
    def error_response(cls, error: str) -> "AgentCallResponse":
        """Create an error response."""
        return cls(success=False, error=error)