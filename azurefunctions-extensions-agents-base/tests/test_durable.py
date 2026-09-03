from __future__ import annotations

import asyncio
import math
from contextlib import asynccontextmanager
from types import SimpleNamespace

import azure.functions as func
import pytest

from azurefunctions.extensions.agents.base import bindings, durable
from azurefunctions.extensions.agents.base.durable import (
    DurableAgentContext,
    _canonicalize_json_value,
    _normalize_agent_prompt,
    _parse_activity_input,
)


class _Context:
    instance_id = "instance-1"

    def __init__(self):
        self.calls = []

    def call_activity(self, name, payload):
        self.calls.append(("activity", name, payload))
        return "task"

    def call_activity_with_retry(self, name, retry, payload):
        self.calls.append(("retry", name, retry, payload))
        return "retry-task"


def test_call_agent_schedules_canonical_payload():
    context = _Context()
    proxy = DurableAgentContext(context, "agent_framework")

    task = proxy.call_agent("orders", {"z": 1, "a": [True, None]})

    assert task == "task"
    assert context.calls == [
        (
            "activity",
            "azurefunctions_agents_run_markdown_agent",
            {
                "schema_version": 2,
                "provider_id": "agent_framework",
                "agent_name": "orders",
                "input": {"a": [True, None], "z": 1},
                "durable_instance_id": "instance-1",
            },
        )
    ]


def test_call_agent_schedules_retry_with_same_canonical_payload():
    from azure.durable_functions import RetryOptions

    context = _Context()
    retry_options = RetryOptions(1000, 3)
    proxy = DurableAgentContext(context, "agent_framework")

    task = proxy.call_agent(
        "orders",
        {"z": 1, "a": 2},
        retry_options=retry_options,
    )

    assert task == "retry-task"
    assert context.calls == [
        (
            "retry",
            "azurefunctions_agents_run_markdown_agent",
            retry_options,
            {
                "schema_version": 2,
                "provider_id": "agent_framework",
                "agent_name": "orders",
                "input": {"a": 2, "z": 1},
                "durable_instance_id": "instance-1",
            },
        )
    ]


def test_call_agent_schedules_explicit_provider():
    context = _Context()
    proxy = DurableAgentContext(context, "agent_framework")

    proxy.call_agent("orders", "hello", provider="langgraph")

    assert context.calls[0][2]["provider_id"] == "langgraph"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_call_agent_rejects_nonfinite_numbers(value):
    with pytest.raises(ValueError, match="NaN or infinity"):
        DurableAgentContext(_Context(), "agent_framework").call_agent("orders", value)


def test_parse_activity_input_rejects_unknown_schema():
    with pytest.raises(ValueError, match="schema_version"):
        _parse_activity_input(
            {
                "schema_version": 1,
                "provider_id": "agent_framework",
                "agent_name": "orders",
                "input": "hello",
                "durable_instance_id": "instance-1",
            }
        )


def test_parse_activity_input_rejects_blank_provider():
    with pytest.raises(ValueError, match="provider_id"):
        _parse_activity_input(
            {
                "schema_version": 2,
                "provider_id": " ",
                "agent_name": "orders",
                "input": "hello",
                "durable_instance_id": "instance-1",
            }
        )


def test_normalize_agent_prompt_preserves_strings_and_encodes_json():
    assert _normalize_agent_prompt("hello") == "hello"
    assert _normalize_agent_prompt({"z": 1, "a": 2}) == '{"a":2,"z":1}'


def test_canonicalize_json_value_rejects_non_string_keys():
    with pytest.raises(TypeError, match="keys must be strings"):
        _canonicalize_json_value({1: "value"})


class _CompiledAgent:
    def __init__(self):
        self.calls = []

    @asynccontextmanager
    async def open_agent(self, invocation):
        yield object()

    async def run_agent(self, prompt, invocation):
        self.calls.append((prompt, invocation))
        return f"response:{prompt}"


class _Provider:
    provider_id = "agent_framework"
    distribution_name = "azurefunctions-extensions-agents-framework"

    def __init__(self):
        self.compiled = _CompiledAgent()
        self.compile_calls = []

    def compile_binding(self, **kwargs):
        self.compile_calls.append(kwargs)
        return self.compiled


def _configured_app(tmp_path, monkeypatch):
    provider = _Provider()
    monkeypatch.setattr(bindings, "load_provider", lambda provider_id: provider)
    app = func.FunctionApp()
    bindings.configure_app(
        app,
        provider="agent_framework",
        app_root=tmp_path,
    )
    return app, provider


def test_configure_durable_app_registers_hidden_activity_once(tmp_path, monkeypatch):
    app, _ = _configured_app(tmp_path, monkeypatch)

    durable.configure_durable_app(app)
    durable.configure_durable_app(app)

    names = [function.get_function_name() for function in app.get_functions()]
    assert names == ["azurefunctions_agents_run_markdown_agent"]


def test_hidden_activity_name_collision_is_rejected(tmp_path, monkeypatch):
    app, _ = _configured_app(tmp_path, monkeypatch)

    @app.function_name(name="azurefunctions_agents_run_markdown_agent")
    @app.activity_trigger(input_name="payload")
    def customer_activity(payload):
        return payload

    durable.configure_durable_app(app)

    with pytest.raises(ValueError, match="unique function name"):
        app.get_functions()


def test_hidden_activity_resolves_and_executes_dynamic_agent(tmp_path, monkeypatch):
    instructions = "---\nthis remains: raw\n---\nHandle orders.\n"
    (tmp_path / "orders.agent.md").write_text(instructions, encoding="utf-8")
    app, provider = _configured_app(tmp_path, monkeypatch)
    durable.configure_durable_app(app)
    activity = app.get_functions()[0].get_user_function()
    context = SimpleNamespace(
        function_name="activity",
        invocation_id="invocation-1",
    )

    result = asyncio.run(
        activity(
            {
                "schema_version": 2,
                "provider_id": "agent_framework",
                "agent_name": "orders",
                "input": {"z": 1, "a": 2},
                "durable_instance_id": "instance-1",
            },
            context,
        )
    )

    assert result == 'response:{"a":2,"z":1}'
    assert provider.compile_calls[0]["instructions"] == instructions
    assert provider.compiled.calls[0][0] == '{"a":2,"z":1}'
    assert provider.compiled.calls[0][1].durable_instance_id == "instance-1"


def test_hidden_activity_routes_same_agent_name_by_provider(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    framework = _Provider()
    langgraph = _Provider()
    langgraph.provider_id = "langgraph"
    providers_by_id = {
        "agent_framework": framework,
        "langgraph": langgraph,
    }
    monkeypatch.setattr(
        bindings,
        "load_provider",
        lambda provider_id: providers_by_id[provider_id],
    )
    app = func.FunctionApp()
    bindings.configure_app(
        app,
        provider="agent_framework",
        app_root=tmp_path,
    )
    bindings.configure_agent_provider(app, provider="langgraph")
    durable.configure_durable_app(app)
    activity = app.get_functions()[0].get_user_function()
    context = SimpleNamespace(function_name="activity", invocation_id="invocation-1")

    for provider_id in providers_by_id:
        asyncio.run(
            activity(
                {
                    "schema_version": 2,
                    "provider_id": provider_id,
                    "agent_name": "orders",
                    "input": "hello",
                    "durable_instance_id": "instance-1",
                },
                context,
            )
        )
    asyncio.run(
        activity(
            {
                "schema_version": 2,
                "provider_id": "agent_framework",
                "agent_name": "orders",
                "input": "again",
                "durable_instance_id": "instance-1",
            },
            context,
        )
    )

    assert len(framework.compile_calls) == 1
    assert len(langgraph.compile_calls) == 1


def test_hidden_activity_rejects_unconfigured_provider(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    app, _ = _configured_app(tmp_path, monkeypatch)
    durable.configure_durable_app(app)
    activity = app.get_functions()[0].get_user_function()
    context = SimpleNamespace(function_name="activity", invocation_id="invocation-1")

    with pytest.raises(ValueError, match="configure_agent_provider"):
        asyncio.run(
            activity(
                {
                    "schema_version": 2,
                    "provider_id": "langgraph",
                    "agent_name": "orders",
                    "input": "hello",
                    "durable_instance_id": "instance-1",
                },
                context,
            )
        )


def test_equal_registration_enables_provider_for_durable(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    provider = _Provider()
    monkeypatch.setattr(bindings, "load_provider", lambda provider_id: provider)
    app = func.FunctionApp()

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        app_root=tmp_path,
    )
    async def handler(agent: object) -> None:
        pass

    bindings.configure_agent_provider(app, provider="agent_framework")
    assert bindings._durable_agent(app, "agent_framework", "orders") is not None
