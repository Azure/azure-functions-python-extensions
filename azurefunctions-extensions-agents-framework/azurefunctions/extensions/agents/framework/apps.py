from __future__ import annotations

import os
from collections.abc import Callable, MutableMapping, Sequence
from typing import Any, TypeVar

import azure.functions as func
from agent_framework import (
    CompactionStrategy,
    ContextProvider,
    MiddlewareTypes,
    TokenizerProtocol,
    ToolTypes,
)

from azurefunctions.extensions.agents.base import markdown_agent as base_markdown_agent

from .provider import AGENT_FRAMEWORK_PROVIDER_ID, ClientFactory

_F = TypeVar("_F", bound=Callable[..., Any])


def _provider_options(
    *,
    client_factory: ClientFactory | None = None,
    tools: (
        ToolTypes | Callable[..., Any] | Sequence[ToolTypes | Callable[..., Any]] | None
    ) = None,
    description: str | None = None,
    default_options: Any | None = None,
    context_providers: Sequence[ContextProvider] | None = None,
    middleware: Sequence[MiddlewareTypes] | None = None,
    require_per_service_call_history_persistence: bool | None = None,
    compaction_strategy: CompactionStrategy | None = None,
    tokenizer: TokenizerProtocol | None = None,
    additional_properties: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if client_factory is not None:
        options["client_factory"] = client_factory
    if tools is not None:
        options["tools"] = tools
    if description is not None:
        options["description"] = description
    if default_options is not None:
        options["default_options"] = default_options
    if context_providers is not None:
        options["context_providers"] = context_providers
    if middleware is not None:
        options["middleware"] = middleware
    if require_per_service_call_history_persistence is not None:
        options["require_per_service_call_history_persistence"] = (
            require_per_service_call_history_persistence
        )
    if compaction_strategy is not None:
        options["compaction_strategy"] = compaction_strategy
    if tokenizer is not None:
        options["tokenizer"] = tokenizer
    if additional_properties is not None:
        options["additional_properties"] = additional_properties
    return options


def markdown_agent(
    app: func.FunctionApp,
    *,
    arg_name: str,
    agent_name: str,
    client_factory: ClientFactory,
    app_root: str | os.PathLike[str] | None = None,
    tools: (
        ToolTypes | Callable[..., Any] | Sequence[ToolTypes | Callable[..., Any]] | None
    ) = None,
    description: str | None = None,
    default_options: Any | None = None,
    context_providers: Sequence[ContextProvider] | None = None,
    middleware: Sequence[MiddlewareTypes] | None = None,
    require_per_service_call_history_persistence: bool = False,
    compaction_strategy: CompactionStrategy | None = None,
    tokenizer: TokenizerProtocol | None = None,
    additional_properties: MutableMapping[str, Any] | None = None,
) -> Callable[[_F], _F]:
    options = _provider_options(
        client_factory=client_factory,
        tools=tools,
        description=description,
        default_options=default_options,
        context_providers=context_providers,
        middleware=middleware,
        require_per_service_call_history_persistence=(
            require_per_service_call_history_persistence
        ),
        compaction_strategy=compaction_strategy,
        tokenizer=tokenizer,
        additional_properties=additional_properties,
    )
    return base_markdown_agent(
        app,
        provider=AGENT_FRAMEWORK_PROVIDER_ID,
        arg_name=arg_name,
        agent_name=agent_name,
        app_root=app_root,
        **options,
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
        description: str | None = None,
        default_options: Any | None = None,
        context_providers: Sequence[ContextProvider] | None = None,
        middleware: Sequence[MiddlewareTypes] | None = None,
        require_per_service_call_history_persistence: bool = False,
        compaction_strategy: CompactionStrategy | None = None,
        tokenizer: TokenizerProtocol | None = None,
        additional_properties: MutableMapping[str, Any] | None = None,
        http_auth_level: func.AuthLevel | str = func.AuthLevel.FUNCTION,
    ) -> None:
        super().__init__(
            http_auth_level=http_auth_level,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            app_root=app_root,
            **_provider_options(
                client_factory=client_factory,
                tools=tools,
                description=description,
                default_options=default_options,
                context_providers=context_providers,
                middleware=middleware,
                require_per_service_call_history_persistence=(
                    require_per_service_call_history_persistence
                ),
                compaction_strategy=compaction_strategy,
                tokenizer=tokenizer,
                additional_properties=additional_properties,
            ),
        )

    def markdown_agent(  # type: ignore[override]
        self,
        *,
        arg_name: str,
        agent_name: str,
        client_factory: ClientFactory | None = None,
        app_root: str | os.PathLike[str] | None = None,
        tools: (
            ToolTypes
            | Callable[..., Any]
            | Sequence[ToolTypes | Callable[..., Any]]
            | None
        ) = None,
        description: str | None = None,
        default_options: Any | None = None,
        context_providers: Sequence[ContextProvider] | None = None,
        middleware: Sequence[MiddlewareTypes] | None = None,
        require_per_service_call_history_persistence: bool | None = None,
        compaction_strategy: CompactionStrategy | None = None,
        tokenizer: TokenizerProtocol | None = None,
        additional_properties: MutableMapping[str, Any] | None = None,
    ) -> Callable[[_F], _F]:
        return super().markdown_agent(
            arg_name=arg_name,
            agent_name=agent_name,
            app_root=app_root,
            **_provider_options(
                client_factory=client_factory,
                tools=tools,
                description=description,
                default_options=default_options,
                context_providers=context_providers,
                middleware=middleware,
                require_per_service_call_history_persistence=(
                    require_per_service_call_history_persistence
                ),
                compaction_strategy=compaction_strategy,
                tokenizer=tokenizer,
                additional_properties=additional_properties,
            ),
        )


class DurableAiApp(AiApp, func.DurableAiApp):
    """Microsoft Agent Framework app with optional Durable Agent support."""
