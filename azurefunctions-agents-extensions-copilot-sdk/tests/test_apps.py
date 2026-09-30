from __future__ import annotations

import inspect
from unittest.mock import Mock

import azure.functions as func
from azurefunctions.agents.extensions.copilot_sdk import AgentFunctionApp, apps


def test_typed_api_exposes_only_v1_options():
    assert list(inspect.signature(AgentFunctionApp.__init__).parameters) == [
        "self",
        "client_factory",
        "model",
        "app_root",
        "on_permission_request",
        "provider",
        "tools",
        "http_auth_level",
    ]
    assert list(inspect.signature(AgentFunctionApp.markdown_agent).parameters) == [
        "self",
        "arg_name",
        "agent_name",
        "client_factory",
        "model",
        "on_permission_request",
        "provider",
        "tools",
    ]


def test_typed_agent_function_app_pins_copilot_provider(monkeypatch):
    parent_init = Mock()
    configure_app = Mock()
    monkeypatch.setattr(func.FunctionApp, "__init__", parent_init)
    monkeypatch.setattr(apps, "configure_app", configure_app)
    factory = lambda: object()

    app = AgentFunctionApp(
        client_factory=factory,
        model="gpt-5",
        app_root="app",
    )

    parent_init.assert_called_once_with(http_auth_level=func.AuthLevel.FUNCTION)
    configure_app.assert_called_once_with(
        app,
        provider="copilot_sdk",
        app_root="app",
        provider_options={"client_factory": factory, "model": "gpt-5"},
    )


def test_agent_function_app_uses_function_app_directly():
    assert func.FunctionApp in AgentFunctionApp.__bases__


def test_typed_markdown_agent_forwards_supported_overrides(monkeypatch):
    parent_decorator = Mock(return_value=object())
    monkeypatch.setattr(apps, "base_markdown_agent", parent_decorator)
    app = object.__new__(AgentFunctionApp)
    factory = lambda: object()

    result = app.markdown_agent(
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
        model="gpt-5",
    )

    assert result is parent_decorator.return_value
    parent_decorator.assert_called_once_with(
        app,
        provider="copilot_sdk",
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
        model="gpt-5",
    )
