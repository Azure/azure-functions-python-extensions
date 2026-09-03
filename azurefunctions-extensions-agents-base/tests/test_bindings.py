from __future__ import annotations

import asyncio
import gc
import inspect
import weakref
from contextlib import asynccontextmanager

import azure.functions as func
import pytest

from azurefunctions.extensions.agents.base import AgentCapabilities
from azurefunctions.extensions.agents.base import bindings, providers


class _CompiledAgent:
    def __init__(self):
        self.opened = 0
        self.closed = 0

    @asynccontextmanager
    async def open_agent(self, invocation):
        self.opened += 1
        try:
            yield {"instance": self.opened, "invocation": invocation}
        finally:
            self.closed += 1

    async def run_agent(self, prompt, invocation):
        return prompt


class _Provider:
    provider_id = "agent_framework"
    distribution_name = "azurefunctions-extensions-agents-framework"
    supported_capabilities = frozenset({"skills", "mcp"})

    def __init__(self):
        self.compiled = _CompiledAgent()
        self.compile_args = None

    def compile_binding(self, **kwargs):
        self.compile_args = kwargs
        return self.compiled


@pytest.fixture
def provider(monkeypatch, tmp_path):
    instance = _Provider()
    monkeypatch.setenv("AzureWebJobsScriptRoot", str(tmp_path))
    monkeypatch.setattr(providers, "load_provider", lambda provider_id: instance)
    monkeypatch.setattr(bindings, "load_provider", lambda provider_id: instance)
    return instance


def test_markdown_agent_injects_fresh_context_and_hides_parameter(tmp_path, provider):
    instructions = "---\nnot: parsed\n---\nUse the order API.\n"
    (tmp_path / "orders.agent.md").write_bytes(instructions.encode("utf-8"))
    app = func.FunctionApp()

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        tools=["lookup"],
    )
    async def handler(value: str, agent: object) -> tuple[str, object]:
        return value, agent

    assert list(inspect.signature(handler).parameters) == ["value"]
    assert provider.compile_args == {
        "instructions": instructions,
        "agent_name": "orders",
        "options": {"tools": ["lookup"]},
        "annotation": object,
        "capabilities": AgentCapabilities(),
    }

    first = asyncio.run(handler("one"))
    second = asyncio.run(handler("two"))

    assert first[1]["instance"] == 1
    assert second[1]["instance"] == 2
    assert provider.compiled.opened == provider.compiled.closed == 2


def test_markdown_agent_closes_context_when_handler_fails(tmp_path, provider):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    app = func.FunctionApp()

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
    )
    async def handler(agent: object) -> None:
        raise RuntimeError("handler failed")

    with pytest.raises(RuntimeError, match="handler failed"):
        asyncio.run(handler())

    assert provider.compiled.opened == provider.compiled.closed == 1


def test_markdown_agent_closes_context_when_handler_is_cancelled(tmp_path, provider):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    app = func.FunctionApp()

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
    )
    async def handler(agent: object) -> None:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(handler())

    assert provider.compiled.opened == provider.compiled.closed == 1


def test_markdown_agent_rejects_ambiguous_files(tmp_path, provider):
    (tmp_path / "agents").mkdir()
    (tmp_path / "orders.agent.md").write_text("root", encoding="utf-8")
    (tmp_path / "agents" / "orders.agent.md").write_text("nested", encoding="utf-8")

    with pytest.raises(ValueError, match="ambiguous"):

        @bindings.markdown_agent(
            func.FunctionApp(),
            provider="agent_framework",
            arg_name="agent",
            agent_name="orders",
        )
        async def handler(agent: object) -> None:
            pass


def test_markdown_agent_rejects_symlink_outside_app_root(tmp_path, provider):
    app_root = tmp_path / "app"
    app_root.mkdir()
    outside = tmp_path / "orders.agent.md"
    outside.write_text("outside", encoding="utf-8")
    try:
        (app_root / "orders.agent.md").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation is unavailable: {error}")
    app = func.FunctionApp()
    bindings.configure_app(app, provider="agent_framework", app_root=app_root)

    with pytest.raises(ValueError, match="resolves outside app root"):

        @bindings.markdown_agent(
            app,
            provider="agent_framework",
            arg_name="agent",
            agent_name="orders",
        )
        async def handler(agent: object) -> None:
            pass


@pytest.mark.parametrize(
    "agent_name",
    ["../orders", "agents/orders", r"agents\orders", "C:orders"],
)
def test_markdown_agent_rejects_nonportable_agent_names(
    tmp_path,
    provider,
    agent_name,
):
    app = func.FunctionApp()

    with pytest.raises(ValueError, match="filename component"):

        @bindings.markdown_agent(
            app,
            provider="agent_framework",
            arg_name="agent",
            agent_name=agent_name,
        )
        async def handler(agent: object) -> None:
            pass


def test_function_app_rejects_a_second_default_provider(tmp_path, provider):
    bindings.configure_app(
        func_app := func.FunctionApp(),
        provider="agent_framework",
        app_root=tmp_path,
    )

    with pytest.raises(ValueError, match="already configured with Agent provider"):
        bindings.configure_app(
            func_app,
            provider="langgraph",
            app_root=tmp_path,
        )


def test_function_app_rejects_a_second_binding_provider(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    monkeypatch.setenv("AzureWebJobsScriptRoot", str(tmp_path))
    providers_by_id = {
        "agent_framework": _Provider(),
        "langgraph": _Provider(),
    }
    providers_by_id["langgraph"].provider_id = "langgraph"
    monkeypatch.setattr(
        bindings,
        "load_provider",
        lambda provider_id: providers_by_id[provider_id],
    )
    app = func.FunctionApp()

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        temperature=0.1,
    )
    async def framework_handler(agent: object) -> None:
        pass

    with pytest.raises(ValueError, match="already configured with Agent provider"):
        bindings.markdown_agent(
            app,
            provider="langgraph",
            arg_name="agent",
            agent_name="orders",
            recursion_limit=20,
        )

    assert providers_by_id["agent_framework"].compile_args["options"] == {
        "temperature": 0.1
    }
    assert providers_by_id["langgraph"].compile_args is None


def test_markdown_agent_rejects_per_binding_app_root(tmp_path, provider):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "orders.agent.md").write_text("instructions", encoding="utf-8")
    app = func.FunctionApp()

    bindings.configure_app(app, provider="agent_framework", app_root=first_root)

    with pytest.raises(TypeError, match="app_root is app-scoped"):
        bindings.markdown_agent(
            app,
            provider="agent_framework",
            arg_name="agent",
            agent_name="orders",
            app_root=second_root,
        )


def test_function_app_state_does_not_keep_app_alive(tmp_path, provider):
    app = func.FunctionApp()
    bindings.configure_app(
        app,
        provider="agent_framework",
        app_root=tmp_path,
    )
    app_reference = weakref.ref(app)

    del app
    gc.collect()

    assert app_reference() is None


def test_app_defaults_are_overridden_by_decorator_options(tmp_path, provider):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    app = func.FunctionApp()
    bindings.configure_app(
        app,
        provider="agent_framework",
        app_root=tmp_path,
        provider_options={"temperature": 0.1, "tools": ["default"]},
    )

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
        temperature=0.5,
    )
    async def handler(agent: object) -> None:
        pass

    assert provider.compile_args["options"] == {
        "temperature": 0.5,
        "tools": ["default"],
    }


def test_all_bindings_receive_same_discovered_capabilities(tmp_path, provider):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    (tmp_path / "returns.agent.md").write_text("instructions", encoding="utf-8")
    skill_directory = tmp_path / "skills" / "inventory"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text(
        "---\nname: inventory\ndescription: Inventory lookup\n---\n",
        encoding="utf-8",
    )

    app = func.FunctionApp()
    bindings.configure_app(app, provider="agent_framework", app_root=tmp_path)

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="orders",
    )
    async def handler(agent: object) -> None:
        pass

    first_capabilities = provider.compile_args["capabilities"]

    @bindings.markdown_agent(
        app,
        provider="agent_framework",
        arg_name="agent",
        agent_name="returns",
    )
    async def returns_handler(agent: object) -> None:
        pass

    second_capabilities = provider.compile_args["capabilities"]
    assert tuple(skill.path for skill in first_capabilities.skills) == (
        skill_directory.resolve(),
    )
    assert second_capabilities is first_capabilities


def test_binding_rejects_discovered_capability_for_unsupported_provider(
    tmp_path,
    provider,
):
    provider.supported_capabilities = frozenset()
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")
    skill_directory = tmp_path / "skills" / "inventory"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text(
        "---\nname: inventory\ndescription: Inventory lookup\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="does not support discovered capabilities"):
        app = func.FunctionApp()
        bindings.configure_app(app, provider="agent_framework", app_root=tmp_path)

        @bindings.markdown_agent(
            app,
            provider="agent_framework",
            arg_name="agent",
            agent_name="orders",
        )
        async def handler(agent: object) -> None:
            pass


def test_markdown_agent_requires_async_handler(tmp_path, provider):
    (tmp_path / "orders.agent.md").write_text("instructions", encoding="utf-8")

    with pytest.raises(TypeError, match="async def"):

        @bindings.markdown_agent(
            func.FunctionApp(),
            provider="agent_framework",
            arg_name="agent",
            agent_name="orders",
        )
        def handler(agent: object) -> None:
            pass
