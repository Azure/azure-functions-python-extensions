from .bindings import configure_app, markdown_agent
from .providers import (
    AGENT_PROVIDER_ENTRY_POINT_GROUP,
    AgentProvider,
    CompiledAgent,
    InvocationMetadata,
    load_provider,
)


def configure_durable_app(*args, **kwargs):
    from .durable import configure_durable_app as configure

    return configure(*args, **kwargs)


def durable_orchestration_trigger(*args, **kwargs):
    from .durable import durable_orchestration_trigger as decorate

    return decorate(*args, **kwargs)


__all__ = [
    "AGENT_PROVIDER_ENTRY_POINT_GROUP",
    "AgentProvider",
    "CompiledAgent",
    "InvocationMetadata",
    "configure_app",
    "configure_durable_app",
    "durable_orchestration_trigger",
    "load_provider",
    "markdown_agent",
]

__version__ = "1.0.0b1"
