from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

import azure.functions as func
from copilot.session import PermissionHandler as CopilotPermissionHandler
from copilot.session import ProviderConfig
from copilot.tools import Tool

from azurefunctions.agents.extensions.base import (
    configure_app,
    durable_orchestration_trigger,
)
from azurefunctions.agents.extensions.base import markdown_agent as base_markdown_agent

from .provider import (
    COPILOT_SDK_PROVIDER_ID,
    ClientFactory,
    PermissionHandler,
    _CopilotProviderOptions,
    _cache_client_factory,
    _default_client_factory,
)

_F = TypeVar("_F", bound=Callable[..., Any])


def _provider_options(
    *,
    client_factory: ClientFactory | None = None,
    model: str | None = None,
    on_permission_request: PermissionHandler | None = None,
    provider: ProviderConfig | None = None,
    tools: Tool | Sequence[Tool] | None = None,
    session_options: Mapping[str, object] | None = None,
) -> _CopilotProviderOptions:
    options: _CopilotProviderOptions = {}
    if client_factory is not None:
        options["client_factory"] = _cache_client_factory(client_factory)
    if model is not None:
        options["model"] = model
    if on_permission_request is not None:
        options["on_permission_request"] = on_permission_request
    if provider is not None:
        options["session_provider"] = provider
    if tools is not None:
        options["tools"] = tools
    if session_options is not None:
        options["session_options"] = session_options
    return options


class _CopilotSdkAppMixin:
    def markdown_agent(
        self,
        *,
        arg_name: str,
        agent_name: str,
        client_factory: ClientFactory | None = None,
        model: str | None = None,
        on_permission_request: PermissionHandler | None = None,
        provider: ProviderConfig | None = None,
        tools: Tool | Sequence[Tool] | None = None,
        **session_options: object,
    ) -> Callable[[_F], _F]:
        return base_markdown_agent(
            self,
            provider=COPILOT_SDK_PROVIDER_ID,
            arg_name=arg_name,
            agent_name=agent_name,
            **_provider_options(
                client_factory=client_factory,
                model=model,
                on_permission_request=on_permission_request,
                provider=provider,
                tools=tools,
                session_options=(session_options or None),
            ),
        )


class AgentFunctionApp(
    _CopilotSdkAppMixin,
    func.FunctionApp,
):
    """Azure Functions app configured for GitHub Copilot SDK sessions."""

    def __init__(
        self,
        *,
        model: str | None = None,
        client_factory: ClientFactory | None = None,
        app_root: str | os.PathLike[str] | None = None,
        on_permission_request: PermissionHandler | None = (
            CopilotPermissionHandler.approve_all
        ),
        provider: ProviderConfig | None = None,
        tools: Tool | Sequence[Tool] | None = None,
        session_options: Mapping[str, object] | None = None,
        http_auth_level: func.AuthLevel | str = func.AuthLevel.FUNCTION,
    ) -> None:
        super().__init__(http_auth_level=http_auth_level)
        configure_app(
            self,
            provider=COPILOT_SDK_PROVIDER_ID,
            app_root=app_root,
            provider_options=_provider_options(
                client_factory=(
                    client_factory
                    if client_factory is not None
                    else _default_client_factory
                ),
                model=(model if model is not None else os.environ["COPILOT_MODEL"]),
                on_permission_request=on_permission_request,
                provider=provider,
                tools=tools,
                session_options=session_options,
            ),
        )

    def orchestration_trigger(
        self,
        context_name: str,
        orchestration: str | None = None,
        input_type: type | None = None,
    ) -> Callable[..., Any]:
        return durable_orchestration_trigger(
            self,
            sdk_decorator=super().orchestration_trigger,
            context_name=context_name,
            orchestration=orchestration,
            input_type=input_type,
        )
