# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Types and enums for multi-agent handoff system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    pass


class HandoffMode(Enum):
    """Defines how control flows between agents."""

    SWARM = "swarm"  # Control passes between agents and bubbles up to user
    COORDINATOR = "coordinator"  # Current agent orchestrates others and returns result
    SEQUENTIAL = "sequential"  # Linear handoff chain
    CONDITIONAL = "conditional"  # Handoff based on conditions


class HandoffStrategy(Enum):
    """Strategies for selecting which agent to hand off to."""

    DIRECT = "direct"  # Hand off to specific named agent
    ROUTE = "route"  # Use routing function to determine target
    BROADCAST = "broadcast"  # Send to multiple agents
    BEST_MATCH = "best_match"  # AI-powered agent selection


class ControlReturn(Enum):
    """Defines what happens after an agent completes its task."""

    BUBBLE_UP = "bubble_up"  # Return control to user/caller
    RETURN_TO_CALLER = "return_to_caller"  # Return to the agent that called this one
    CONTINUE_CHAIN = "continue_chain"  # Continue to next agent in chain
    END_CONVERSATION = "end_conversation"  # End the conversation


@dataclass
class HandoffTarget:
    """Defines a specific handoff target with conditions."""

    agent_name: str
    condition: Optional[Union[str, Callable[..., bool]]] = None
    context_keys: Optional[List[str]] = None  # Context to pass along
    transform_input: Optional[
        Callable[[Any], Any]
    ] = None  # Transform input before handoff
    description: Optional[str] = None


@dataclass
class HandoffConfig:
    """Configuration for agent handoff behavior."""

    mode: HandoffMode = HandoffMode.SWARM
    strategy: HandoffStrategy = HandoffStrategy.DIRECT
    targets: List[HandoffTarget] = field(default_factory=list)
    default_return: ControlReturn = ControlReturn.BUBBLE_UP
    max_hops: int = 10  # Prevent infinite loops
    enable_auto_routing: bool = False  # AI-powered routing
    routing_instructions: Optional[str] = None  # Instructions for AI routing


@dataclass
class HandoffContext:
    """Context passed between agents during handoff."""

    conversation_id: str
    call_stack: List[str] = field(default_factory=list)  # Track agent call hierarchy
    shared_context: Dict[str, Any] = field(default_factory=dict)
    handoff_count: int = 0
    max_hops: int = 10
    original_request: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class HandoffResult:
    """Result of a handoff operation."""

    success: bool
    target_agent: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    control_return: ControlReturn = ControlReturn.BUBBLE_UP
    error: Optional[str] = None
    context: Optional[HandoffContext] = None
    execution_path: List[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Standardized agent response with handoff information."""

    agent_name: str
    content: Any
    handoff_request: Optional["HandoffRequest"] = None
    control_return: ControlReturn = ControlReturn.BUBBLE_UP
    context_updates: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HandoffRequest:
    """Request to hand off control to another agent."""

    target_agent: str
    input_data: Any
    reason: Optional[str] = None
    context_keys: Optional[List[str]] = None  # Specific context to pass
    expected_return: ControlReturn = ControlReturn.RETURN_TO_CALLER
    timeout: Optional[int] = None
    transform_response: Optional[Callable[[Any], Any]] = None
