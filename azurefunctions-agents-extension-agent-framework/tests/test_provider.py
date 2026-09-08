from __future__ import annotations

import asyncio
import inspect
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from agent_framework import Agent

from azurefunctions.extensions.agents.base import (
    AgentCapabilities,
    InvocationMetadata,
    MCPHTTPConfig,
    MCPServerDefinition,
    SkillDefinition,
)
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


def _compile(*, capabilities=AgentCapabilities(), **overrides):
    options = {"client_factory": lambda: object(), "tools": ["lookup"]}
    options.update(overrides)
    return provider.AgentFrameworkProvider().compile_binding(
        instructions="raw instructions",
        agent_name="orders",
        options=options,
        annotation=Agent,
        capabilities=capabilities,
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
            capabilities=AgentCapabilities(),
        )


def test_provider_accepts_missing_annotation_for_durable_activity():
    binding = provider.AgentFrameworkProvider().compile_binding(
        instructions="instructions",
        agent_name="orders",
        options={"client_factory": lambda: object()},
        annotation=inspect.Signature.empty,
        capabilities=AgentCapabilities(),
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
            capabilities=AgentCapabilities(),
        )


def test_provider_rejects_non_callable_client_factory():
    with pytest.raises(TypeError, match="client_factory must be callable"):
        _compile(client_factory="not callable")


def test_provider_rejects_async_client_factory():
    async def create_client():
        return object()

    with pytest.raises(
        TypeError, match="client_factory must be a synchronous function"
    ):
        _compile(client_factory=create_client)


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


def test_binding_translates_and_closes_capabilities(monkeypatch):
    skill = SkillDefinition(Path("inventory"))
    server = MCPServerDefinition(
        "orders",
        MCPHTTPConfig("https://mcp.example.test"),
    )
    mcp_events = []
    skill_providers = []

    def build_skills(skills):
        skills_provider = {"paths": tuple(item.path for item in skills)}
        skill_providers.append(skills_provider)
        return skills_provider

    @asynccontextmanager
    async def open_mcp(definition):
        tool = {"server": definition.name, "instance": len(mcp_events)}
        mcp_events.append(("open", tool))
        try:
            yield tool
        finally:
            mcp_events.append(("close", tool))

    monkeypatch.setattr(provider, "_build_skills_provider", build_skills)
    monkeypatch.setattr(provider, "_open_mcp_tool", open_mcp)
    binding = _compile(
        capabilities=AgentCapabilities(
            skills=(skill,),
            mcp_servers=(server,),
        )
    )

    async def invoke_twice():
        async with binding.open_agent(InvocationMetadata()):
            assert mcp_events[-1][0] == "open"
        async with binding.open_agent(InvocationMetadata()):
            assert mcp_events[-1][0] == "open"

    asyncio.run(invoke_twice())

    assert len(skill_providers) == 2
    assert [event for event, _ in mcp_events] == [
        "open",
        "close",
        "open",
        "close",
    ]
    assert _Agent.created[0].kwargs["context_providers"] == [skill_providers[0]]
    assert _Agent.created[0].kwargs["tools"][0] == "lookup"
    assert _Agent.created[0].kwargs["tools"][1]["server"] == "orders"
    assert _Agent.created[0].closed


def test_binding_enters_mcp_tool_once_through_agent(monkeypatch):
    import agent_framework

    events = []

    class FakeTool:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            events.append("connect")
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            events.append("close")

    class AgentOwningTools(_Agent):
        async def __aenter__(self):
            await super().__aenter__()
            self.tool_stack = AsyncExitStack()
            await self.tool_stack.__aenter__()
            for tool in self.kwargs.get("tools", []):
                if isinstance(tool, FakeTool):
                    await self.tool_stack.enter_async_context(tool)
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            await self.tool_stack.__aexit__(exc_type, exc_value, traceback)
            await super().__aexit__(exc_type, exc_value, traceback)

    monkeypatch.setattr(agent_framework, "MCPStreamableHTTPTool", FakeTool)
    monkeypatch.setattr(provider, "Agent", AgentOwningTools)
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "orders",
                    MCPHTTPConfig("https://mcp.example.test"),
                ),
            ),
        )
    )

    async def invoke():
        async with binding.open_agent(InvocationMetadata()):
            assert events == ["connect"]

    asyncio.run(invoke())

    assert events == ["connect", "close"]


def test_skills_provider_owns_skill_format_validation(monkeypatch):
    from_paths = Mock(return_value=object())
    monkeypatch.setattr(provider.SkillsProvider, "from_paths", from_paths)
    skill_path = Path("skills/inventory")

    result = provider._build_skills_provider((SkillDefinition(skill_path),))

    assert result is from_paths.return_value
    from_paths.assert_called_once_with(
        [skill_path],
        disable_load_skill_approval=True,
        disable_read_skill_resource_approval=True,
    )


def test_environment_resolution_reports_names_without_values(monkeypatch):
    monkeypatch.delenv("PRIVATE_MCP_TOKEN", raising=False)

    with pytest.raises(ValueError, match="PRIVATE_MCP_TOKEN") as error:
        provider._resolve_environment(
            "Bearer $PRIVATE_MCP_TOKEN",
            field="header Authorization",
        )

    assert "Bearer" not in str(error.value)


@pytest.mark.parametrize("resolved_url", ["file:///etc/passwd", "ftp://host/path"])
def test_mcp_url_is_validated_after_environment_resolution(
    monkeypatch,
    resolved_url,
):
    monkeypatch.setenv("MCP_SERVER_URL", resolved_url)
    definition = MCPServerDefinition(
        "orders",
        MCPHTTPConfig("$MCP_SERVER_URL"),
    )

    async def open_tool():
        async with provider._open_mcp_tool(definition):
            pass

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        asyncio.run(open_tool())


def test_mcp_client_does_not_follow_redirects(monkeypatch):
    import agent_framework
    import httpx

    client_options = []

    class FakeClient:
        def __init__(self, **kwargs):
            client_options.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

    class FakeTool:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(agent_framework, "MCPStreamableHTTPTool", FakeTool)
    definition = MCPServerDefinition(
        "orders",
        MCPHTTPConfig(
            "https://mcp.example.test",
            headers=(("X-Tenant", "contoso"),),
        ),
    )

    async def open_tool():
        async with provider._open_mcp_tool(definition):
            pass

    asyncio.run(open_tool())

    assert client_options[0]["follow_redirects"] is False
