from __future__ import annotations

import inspect
from unittest.mock import Mock

import azure.functions as func

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.agent_framework import apps


def test_typed_api_exposes_only_v1_options():
    assert list(inspect.signature(AgentFunctionApp.__init__).parameters) == [
        "self",
        "client_factory",
        "app_root",
        "tools",
        "http_auth_level",
        "durable",
        "workflows",
        "workflow_factory",
    ]
    assert list(inspect.signature(AgentFunctionApp.markdown_agent).parameters) == [
        "self",
        "arg_name",
        "agent_name",
        "client_factory",
        "tools",
    ]
    assert list(
        inspect.signature(AgentFunctionApp.orchestration_trigger).parameters
    ) == [
        "self",
        "context_name",
        "orchestration",
        "input_type",
    ]


def test_typed_agent_function_app_pins_framework_provider(monkeypatch):
    parent_init = Mock()
    configure_app = Mock()
    monkeypatch.setattr(func.FunctionApp, "__init__", parent_init)
    monkeypatch.setattr(apps, "configure_app", configure_app)
    factory = lambda: object()

    app = AgentFunctionApp(
        client_factory=factory,
        app_root="app",
        tools=["lookup"],
    )

    parent_init.assert_called_once_with(
        http_auth_level=func.AuthLevel.FUNCTION,
    )
    configure_app.assert_called_once_with(
        app,
        provider="agent_framework",
        app_root="app",
        provider_options={"client_factory": factory, "tools": ["lookup"]},
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
        tools=["lookup"],
    )

    assert result is parent_decorator.return_value
    parent_decorator.assert_called_once_with(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
        tools=["lookup"],
    )


def test_typed_orchestration_trigger_keeps_native_context(monkeypatch):
    parent_decorator = Mock(return_value=object())

    def sdk(context_name, orchestration=None, input_type=None):
        assert (context_name, orchestration, input_type) == ("context", "orders", dict)
        return parent_decorator

    monkeypatch.setattr(
        func.FunctionApp,
        "orchestration_trigger",
        staticmethod(sdk),
    )
    app = object.__new__(AgentFunctionApp)

    result = app.orchestration_trigger(
        context_name="context",
        orchestration="orders",
        input_type=dict,
    )

    def handler(context):
        yield context

    assert result(handler) is parent_decorator.return_value
    parent_decorator.assert_called_once_with(handler)
