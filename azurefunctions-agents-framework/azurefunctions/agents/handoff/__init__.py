# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Multi-agent handoff system for Azure Functions Agent Framework."""

from .types import (
    HandoffMode,
    HandoffStrategy,
    ControlReturn,
    HandoffTarget,
    HandoffConfig,
    HandoffContext,
    HandoffRequest,
    HandoffResult,
    AgentResponse
)

from .control_flow import ControlFlowManager
from .engine import HandoffEngine

__all__ = [
    "HandoffMode",
    "HandoffStrategy", 
    "ControlReturn",
    "HandoffTarget",
    "HandoffConfig",
    "HandoffContext",
    "HandoffRequest",
    "HandoffResult",
    "AgentResponse",
    "ControlFlowManager",
    "HandoffEngine"
]
