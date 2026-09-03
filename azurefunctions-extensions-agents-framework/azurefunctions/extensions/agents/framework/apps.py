from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import azure.functions as func
from agent_framework import ToolTypes

from azurefunctions.extensions.agents.base import markdown_agent as base_markdown_agent

from .provider import AGENT_FRAMEWORK_PROVIDER_ID, ClientFactory

_F = TypeVar("_F", bound=Callable[..., Any])


def _provider_options(
    *,
    client_factory: ClientFactory | None = None,
    tools: (
        ToolTypes | Callable[..., Any] | Sequence[ToolTypes | Callable[..., Any]] | None
    ) = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if client_factory is not None:
        options["client_factory"] = client_factory
    if tools is not None:
        options["tools"] = tools
    return options


def markdown_agent(
    app: func.FunctionApp,
    *,
    arg_name: str,
    agent_name: str,
    client_factory: ClientFactory | None = None,
    tools: (
        ToolTypes | Callable[..., Any] | Sequence[ToolTypes | Callable[..., Any]] | None
    ) = None,
) -> Callable[[_F], _F]:
    return base_markdown_agent(
        app,
        provider=AGENT_FRAMEWORK_PROVIDER_ID,
        arg_name=arg_name,
        agent_name=agent_name,
        **_provider_options(client_factory=client_factory, tools=tools),
    )


class AiApp(func.AiApp):
    """Azure Functions app configured for Microsoft Agent Framework."""

    def __init__(
        self,
        *,
        client_factory: ClientFactory,
        app_root: str | os.PathLike[str] | None = None,
        tools: (
            ToolTypes
            | Callable[..., Any]
            | Sequence[ToolTypes | Callable[..., Any]]
            | None
        ) = None,
        http_auth_level: func.AuthLevel | str = func.AuthLevel.FUNCTION,
    ) -> None:
        super().__init__(
            http_auth_level=http_auth_level,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            app_root=app_root,
            **_provider_options(client_factory=client_factory, tools=tools),
        )

    def markdown_agent(
        self,
        *,
        arg_name: str,
        agent_name: str,
        client_factory: ClientFactory | None = None,
        tools: (
            ToolTypes
            | Callable[..., Any]
            | Sequence[ToolTypes | Callable[..., Any]]
            | None
        ) = None,
    ) -> Callable[[_F], _F]:
        return super().markdown_agent(
            arg_name=arg_name,
            agent_name=agent_name,
            **_provider_options(client_factory=client_factory, tools=tools),
        )


class DurableAiApp(AiApp, func.DurableAiApp):
    """Microsoft Agent Framework app with optional Durable Agent support."""
