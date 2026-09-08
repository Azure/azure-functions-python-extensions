from typing import Any

from .bindings import configure_app, markdown_agent
from .capabilities import (
    AgentCapabilities,
    MCPAuthConfig,
    MCPHTTPConfig,
    MCPServerDefinition,
    SkillDefinition,
)
from .providers import (
    AGENT_PROVIDER_ENTRY_POINT_GROUP,
    AgentProvider,
    CompiledAgent,
    InvocationMetadata,
    load_provider,
)


def configure_durable_app(*args: Any, **kwargs: Any) -> Any:
    from .durable import configure_durable_app as configure

    return configure(*args, **kwargs)


def durable_orchestration_trigger(*args: Any, **kwargs: Any) -> Any:
    from .durable import durable_orchestration_trigger as decorate

    return decorate(*args, **kwargs)


__all__ = [
    "AGENT_PROVIDER_ENTRY_POINT_GROUP",
    "AgentCapabilities",
    "AgentProvider",
    "CompiledAgent",
    "InvocationMetadata",
    "MCPAuthConfig",
    "MCPHTTPConfig",
    "MCPServerDefinition",
    "SkillDefinition",
    "configure_app",
    "configure_durable_app",
    "durable_orchestration_trigger",
    "load_provider",
    "markdown_agent",
]

__version__ = "1.0.0b1"
