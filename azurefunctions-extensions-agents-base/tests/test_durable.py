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
    proxy = DurableAgentContext(context)

    task = proxy.call_agent("orders", {"z": 1, "a": [True, None]})

    assert task == "task"
    assert context.calls == [
        (
            "activity",
            "azurefunctions_agents_run_markdown_agent",
            {
                "schema_version": 1,
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
    proxy = DurableAgentContext(context)

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
                "schema_version": 1,
                "agent_name": "orders",
                "input": {"a": 2, "z": 1},
                "durable_instance_id": "instance-1",
            },
        )
    ]


def test_call_agent_does_not_accept_provider_override():
    with pytest.raises(TypeError, match="provider"):
        DurableAgentContext(_Context()).call_agent(
            "orders",
            "hello",
            provider="langgraph",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_call_agent_rejects_nonfinite_numbers(value):
    with pytest.raises(ValueError, match="NaN or infinity"):
        DurableAgentContext(_Context()).call_agent("orders", value)


def test_parse_activity_input_rejects_unknown_schema():
    with pytest.raises(ValueError, match="schema_version"):
        _parse_activity_input(
            {
                "schema_version": 2,
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
    supported_capabilities = frozenset({"skills", "mcp"})

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
    (tmp_path / "orders.agent.md").write_bytes(instructions.encode("utf-8"))
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
                "schema_version": 1,
                "agent_name": "orders",
                "input": {"z": 1, "a": 2},
                "durable_instance_id": "instance-1",
            },
            context,
        )
    )

    assert result == 'response:{"a":2,"z":1}'
    assert provider.compile_calls[0]["instructions"] == instructions
    assert provider.compile_calls[0]["capabilities"].skills == ()
    assert provider.compiled.calls[0][0] == '{"a":2,"z":1}'
    assert provider.compiled.calls[0][1].durable_instance_id == "instance-1"
    asyncio.run(
        activity(
            {
                "schema_version": 1,
                "agent_name": "orders",
                "input": "again",
                "durable_instance_id": "instance-1",
            },
            context,
        )
    )
    assert len(provider.compile_calls) == 1


def test_hidden_activity_receives_all_discovered_capabilities(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    skill_directory = tmp_path / "skills" / "inventory"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text(
        "---\nname: inventory\ndescription: Inventory lookup\n---\n",
        encoding="utf-8",
    )
    app, provider = _configured_app(tmp_path, monkeypatch)
    durable.configure_durable_app(app)
    activity = app.get_functions()[0].get_user_function()

    asyncio.run(
        activity(
            {
                "schema_version": 1,
                "agent_name": "orders",
                "input": "hello",
                "durable_instance_id": "instance-1",
            },
            SimpleNamespace(function_name="activity", invocation_id="invocation-1"),
        )
    )

    capabilities = provider.compile_calls[0]["capabilities"]
    assert tuple(skill.path for skill in capabilities.skills) == (
        skill_directory.resolve(),
    )
