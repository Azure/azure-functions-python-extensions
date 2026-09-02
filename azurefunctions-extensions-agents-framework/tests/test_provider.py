from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from agent_framework import Agent

from azurefunctions.extensions.agents.base import InvocationMetadata
from azurefunctions.extensions.agents.framework import provider


class _Agent:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.entered = False
        self.closed = False
        self.created.append(self)

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True

    async def run(self, prompt):
        return SimpleNamespace(text=f"response:{prompt}")


@pytest.fixture(autouse=True)
def fake_agent(monkeypatch):
    _Agent.created.clear()
    monkeypatch.setattr(provider, "Agent", _Agent)


def _compile(**overrides):
    options = {"client_factory": lambda: object(), "tools": ["lookup"]}
    options.update(overrides)
    return provider.AgentFrameworkProvider().compile_binding(
        instructions="raw instructions",
        agent_name="orders",
        options=options,
        annotation=Agent,
    )


def test_binding_creates_and_closes_fresh_agents():
    binding = _compile()

    async def invoke_twice():
        async with binding.open_agent(InvocationMetadata()) as first:
            assert first.entered
        async with binding.open_agent(InvocationMetadata()) as second:
            assert second.entered

    asyncio.run(invoke_twice())

    assert len(_Agent.created) == 2
    assert all(agent.closed for agent in _Agent.created)
    assert _Agent.created[0].kwargs["client"] is not _Agent.created[1].kwargs["client"]
    assert _Agent.created[0].kwargs == {
        "client": _Agent.created[0].kwargs["client"],
        "instructions": "raw instructions",
        "name": "orders",
        "tools": ["lookup"],
    }


def test_binding_run_agent_returns_response_text():
    assert (
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))
        == "response:hello"
    )
    assert _Agent.created[0].closed


def test_provider_rejects_non_agent_annotation():
    with pytest.raises(TypeError, match="agent_framework.Agent"):
        provider.AgentFrameworkProvider().compile_binding(
            instructions="instructions",
            agent_name="orders",
            options={"client_factory": lambda: object()},
            annotation=str,
        )


def test_provider_accepts_missing_annotation_for_durable_activity():
    binding = provider.AgentFrameworkProvider().compile_binding(
        instructions="instructions",
        agent_name="orders",
        options={"client_factory": lambda: object()},
        annotation=inspect.Signature.empty,
    )

    assert binding.agent_name == "orders"


def test_provider_rejects_unknown_options():
    with pytest.raises(TypeError, match="unknown"):
        _compile(unknown=True)


def test_provider_requires_client_factory():
    with pytest.raises(TypeError, match="client_factory"):
        provider.AgentFrameworkProvider().compile_binding(
            instructions="instructions",
            agent_name="orders",
            options={},
            annotation=Agent,
        )


def test_provider_rejects_non_callable_client_factory():
    with pytest.raises(TypeError, match="client_factory must be callable"):
        _compile(client_factory="not callable")


def test_provider_factory_errors_propagate():
    def fail():
        raise RuntimeError("client failed")

    binding = _compile(client_factory=fail)

    with pytest.raises(RuntimeError, match="client failed"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))


def test_binding_rejects_non_string_response_text(monkeypatch):
    async def run_without_text(self, prompt):
        return SimpleNamespace(text=None)

    monkeypatch.setattr(_Agent, "run", run_without_text)

    with pytest.raises(TypeError, match="response.text must be a string"):
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))

    assert _Agent.created[0].closed
