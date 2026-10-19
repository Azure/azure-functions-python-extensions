from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

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

if TYPE_CHECKING:
    from .durable import _DurableApp

_F = TypeVar("_F", bound=Callable[..., Any])


def configure_durable_app(app: _DurableApp) -> None:
    from .durable import configure_durable_app as configure

    configure(app)


def durable_orchestration_trigger(
    app: _DurableApp,
    *,
    sdk_decorator: Callable[..., Any],
    context_name: str,
    orchestration: str | None = None,
    input_type: type | None = None,
) -> Callable[[_F], Any]:
    from .durable import durable_orchestration_trigger as decorate

    return decorate(
        app,
        sdk_decorator=sdk_decorator,
        context_name=context_name,
        orchestration=orchestration,
        input_type=input_type,
    )


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

__version__ = '1.0.0b1'
