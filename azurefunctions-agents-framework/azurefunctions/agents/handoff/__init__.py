# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Multi-agent handoff system for Azure Functions Agent Framework."""

from .control_flow import ControlFlowManager
from .engine import HandoffEngine
from .types import (
    AgentResponse,
    ControlReturn,
    HandoffConfig,
    HandoffContext,
    HandoffMode,
    HandoffRequest,
    HandoffResult,
    HandoffStrategy,
    HandoffTarget,
)

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
    "HandoffEngine",
]
