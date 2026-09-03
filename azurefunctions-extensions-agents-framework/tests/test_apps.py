from __future__ import annotations

from unittest.mock import Mock

import azure.functions as func

from azurefunctions.extensions.agents.framework import (
    AiApp,
    DurableAiApp,
    markdown_agent,
)
from azurefunctions.extensions.agents.framework import apps


def test_typed_ai_app_pins_framework_provider(monkeypatch):
    parent_init = Mock()
    monkeypatch.setattr(func.AiApp, "__init__", parent_init)
    factory = lambda: object()

    AiApp(client_factory=factory, app_root="app", description="orders")

    parent_init.assert_called_once_with(
        http_auth_level=func.AuthLevel.FUNCTION,
        provider="agent_framework",
        app_root="app",
        client_factory=factory,
        description="orders",
        require_per_service_call_history_persistence=False,
    )


def test_typed_markdown_agent_forwards_supported_overrides(monkeypatch):
    parent_decorator = Mock(return_value=object())
    monkeypatch.setattr(func.AiApp, "markdown_agent", parent_decorator)
    app = object.__new__(AiApp)
    factory = lambda: object()

    result = app.markdown_agent(
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
        tools=["lookup"],
    )

    assert result is parent_decorator.return_value
    parent_decorator.assert_called_once_with(
        arg_name="agent",
        agent_name="orders",
        app_root=None,
        client_factory=factory,
        tools=["lookup"],
    )


def test_typed_decorator_preserves_app_provider_defaults(monkeypatch):
    base_decorator = Mock(return_value=object())
    monkeypatch.setattr(apps, "base_markdown_agent", base_decorator)
    app = func.FunctionApp()
    factory = lambda: object()

    result = markdown_agent(
        app,
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
    )

    assert result is base_decorator.return_value
    base_decorator.assert_called_once_with(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        app_root=None,
        client_factory=factory,
    )


def test_typed_durable_ai_app_is_typed_ai_app():
    assert issubclass(DurableAiApp, AiApp)
    assert issubclass(DurableAiApp, func.DurableAiApp)
