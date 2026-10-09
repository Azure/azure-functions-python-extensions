from __future__ import annotations

import inspect
from unittest.mock import Mock

import azure.functions as func
from copilot.session import PermissionHandler
from azurefunctions.agents.extensions.copilot_sdk import (
    AgentFunctionApp,
    apps,
)


def test_api_exposes_extension_options_and_arbitrary_session_options():
    assert list(inspect.signature(AgentFunctionApp.__init__).parameters) == [
        "self",
        "model",
        "client_factory",
        "app_root",
        "on_permission_request",
        "provider",
        "tools",
        "session_options",
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
        "session_options",
    ]
    assert (
        inspect.signature(AgentFunctionApp.markdown_agent)
        .parameters["session_options"]
        .kind
        is inspect.Parameter.VAR_KEYWORD
    )


def test_typed_agent_function_app_pins_copilot_provider(monkeypatch):
    parent_init = Mock()
    configure_app = Mock()
    monkeypatch.setattr(func.FunctionApp, "__init__", parent_init)
    monkeypatch.setattr(apps, "configure_app", configure_app)
    factory = lambda: object()
    permission_handler = lambda *args: None

    AgentFunctionApp(
        client_factory=factory,
        model="gpt-5",
        app_root="app",
        on_permission_request=permission_handler,
    )

    parent_init.assert_called_once_with(http_auth_level=func.AuthLevel.FUNCTION)
    options = configure_app.call_args.kwargs["provider_options"]
    assert callable(options["client_factory"])
    assert options["client_factory"] is not factory
    assert options["model"] == "gpt-5"
    assert options["on_permission_request"] is permission_handler
    assert configure_app.call_args.kwargs["provider"] == "copilot_sdk"
    assert configure_app.call_args.kwargs["app_root"] == "app"


def test_typed_agent_function_app_configures_default_client(monkeypatch):
    parent_init = Mock()
    configure_app = Mock()
    monkeypatch.setattr(func.FunctionApp, "__init__", parent_init)
    monkeypatch.setattr(apps, "configure_app", configure_app)
    monkeypatch.setenv("COPILOT_MODEL", "gpt-5")

    AgentFunctionApp()

    options = configure_app.call_args.kwargs["provider_options"]
    assert callable(options["client_factory"])
    assert options["model"] == "gpt-5"
    assert options["on_permission_request"] is PermissionHandler.approve_all


def test_agent_function_app_uses_function_app_directly():
    assert func.FunctionApp in AgentFunctionApp.__bases__


def test_typed_markdown_agent_forwards_arbitrary_session_options(monkeypatch):
    parent_decorator = Mock(return_value=object())
    monkeypatch.setattr(apps, "base_markdown_agent", parent_decorator)
    app = object.__new__(AgentFunctionApp)
    factory = lambda: object()

    result = app.markdown_agent(
        arg_name="agent",
        agent_name="orders",
        client_factory=factory,
        model="gpt-5",
        streaming=True,
        custom_session_option="value",
    )

    assert result is parent_decorator.return_value
    call = parent_decorator.call_args
    assert call.args == (app,)
    assert call.kwargs["provider"] == "copilot_sdk"
    assert call.kwargs["arg_name"] == "agent"
    assert call.kwargs["agent_name"] == "orders"
    assert callable(call.kwargs["client_factory"])
    assert call.kwargs["client_factory"] is not factory
    assert call.kwargs["model"] == "gpt-5"
    assert call.kwargs["session_options"] == {
        "streaming": True,
        "custom_session_option": "value",
    }


def test_typed_markdown_agent_forwards_sdk_provider_without_keyword_collision(
    monkeypatch,
):
    parent_decorator = Mock(return_value=object())
    monkeypatch.setattr(apps, "base_markdown_agent", parent_decorator)
    app = object.__new__(AgentFunctionApp)
    sdk_provider = {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://models.example.test",
        "api_key": "test-key",
    }

    result = app.markdown_agent(
        arg_name="agent",
        agent_name="orders",
        provider=sdk_provider,
    )

    assert result is parent_decorator.return_value
    call = parent_decorator.call_args
    assert call.kwargs["provider"] == "copilot_sdk"
    assert call.kwargs["session_provider"] is sdk_provider


def test_typed_markdown_agent_omits_empty_session_options(monkeypatch):
    parent_decorator = Mock(return_value=object())
    monkeypatch.setattr(apps, "base_markdown_agent", parent_decorator)
    app = object.__new__(AgentFunctionApp)

    app.markdown_agent(
        arg_name="agent",
        agent_name="orders",
    )

    assert "session_options" not in parent_decorator.call_args.kwargs
