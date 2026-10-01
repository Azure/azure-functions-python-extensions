from __future__ import annotations

import asyncio
import inspect
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from azurefunctions.agents.extensions.base import (
    AgentCapabilities,
    InvocationMetadata,
    MCPAuthConfig,
    MCPHTTPConfig,
    MCPServerDefinition,
    SkillDefinition,
)
from azurefunctions.agents.extensions.copilot_sdk import provider
from copilot.session import CopilotSession
from copilot.session_events import AssistantMessageData
from copilot.tools import Tool


class _Session:
    def __init__(self) -> None:
        self.entered = False
        self.closed = False
        self.prompts: list[str] = []

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True

    async def send_and_wait(self, prompt: str):
        self.prompts.append(prompt)
        return SimpleNamespace(
            data=AssistantMessageData(
                content=f"response:{prompt}",
                message_id="message-1",
            )
        )


class _Client:
    created: list[_Client] = []

    def __init__(self, **options) -> None:
        self.entered = False
        self.closed = False
        self.client_options = options
        self.sessions: list[_Session] = []
        self.session_options = None
        self.created.append(self)

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True

    async def create_session(self, **options):
        session = _Session()
        self.sessions.append(session)
        self.session_options = options
        return session


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    _Client.created.clear()
    monkeypatch.setattr(provider, "CopilotClient", _Client)


def _compile(*, capabilities=AgentCapabilities(), **overrides):
    options = {"client_factory": _Client, "model": "gpt-5"}
    options.update(overrides)
    return provider.CopilotSdkProvider().compile_binding(
        instructions="raw instructions",
        agent_name="orders",
        options=options,
        annotation=CopilotSession,
        capabilities=capabilities,
    )


def test_binding_reuses_client_and_closes_fresh_sessions():
    binding = _compile()

    async def invoke_twice():
        async with binding.open_agent(InvocationMetadata()) as first:
            assert first.entered
        async with binding.open_agent(InvocationMetadata()) as second:
            assert second.entered

    asyncio.run(invoke_twice())

    assert len(_Client.created) == 1
    assert not _Client.created[0].closed
    assert len(_Client.created[0].sessions) == 2
    assert all(session.closed for session in _Client.created[0].sessions)
    options = _Client.created[0].session_options
    assert options["model"] == "gpt-5"
    assert options["system_message"] == {
        "mode": "replace",
        "content": "raw instructions",
    }
    assert options["enable_config_discovery"] is False
    assert options["enable_session_store"] is False
    assert options["included_builtin_skills"] == []
    assert list(options["available_tools"]) == []


def test_binding_applies_create_session_overrides():
    binding = _compile(
        session_options={
            "streaming": True,
            "enable_session_store": True,
            "reasoning_effort": "high",
            "system_message": {"mode": "append", "content": "extra"},
        }
    )

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    options = _Client.created[0].session_options
    assert options["streaming"] is True
    assert options["enable_session_store"] is True
    assert options["reasoning_effort"] == "high"
    assert options["system_message"] == {"mode": "append", "content": "extra"}


def test_binding_applies_sdk_provider():
    sdk_provider = {
        "type": "openai",
        "wire_api": "responses",
        "base_url": "https://models.example.test",
        "api_key": "test-key",
    }
    binding = _compile(session_provider=sdk_provider)

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert _Client.created[0].session_options["provider"] is sdk_provider


def test_provider_rejects_unknown_create_session_override():
    with pytest.raises(TypeError, match="Unsupported Copilot create_session option"):
        _compile(session_options={"not_a_session_option": True})


def test_client_cache_is_safe_during_concurrent_first_use():
    factory_calls = 0

    def create_client():
        nonlocal factory_calls
        factory_calls += 1
        time.sleep(0.01)
        return _Client()

    binding = _compile(client_factory=create_client)

    with ThreadPoolExecutor(max_workers=8) as executor:
        clients = list(
            executor.map(
                lambda _: binding.options.client_factory(),
                range(8),
            )
        )

    assert factory_calls == 1
    assert all(client is clients[0] for client in clients)


def test_app_level_client_cache_is_shared_across_bindings():
    client_factory = provider._cache_client_factory(_Client)

    first = _compile(client_factory=client_factory)
    second = _compile(client_factory=client_factory)

    assert first.options.client_factory() is second.options.client_factory()
    assert len(_Client.created) == 1


def test_binding_run_agent_returns_assistant_content():
    assert (
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))
        == "response:hello"
    )
    assert _Client.created[0].sessions[0].prompts == ["hello"]
    assert not _Client.created[0].closed


def test_provider_uses_secure_default_client_and_validates_options(monkeypatch):
    monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("COPILOT_BASE_DIRECTORY", "copilot-data")
    binding = provider.CopilotSdkProvider().compile_binding(
        instructions="instructions",
        agent_name="orders",
        options={"model": "gpt-5"},
        annotation=CopilotSession,
        capabilities=AgentCapabilities(),
    )

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert _Client.created[0].client_options == {
        "mode": "empty",
        "github_token": "github-token",
        "base_directory": "copilot-data",
        "use_logged_in_user": False,
        "log_level": "none",
        "telemetry": None,
    }
    with pytest.raises(TypeError, match="model option"):
        _compile(model="")
    with pytest.raises(TypeError, match="CopilotSession"):
        provider.CopilotSdkProvider().compile_binding(
            instructions="instructions",
            agent_name="orders",
            options={"client_factory": _Client, "model": "gpt-5"},
            annotation=str,
            capabilities=AgentCapabilities(),
        )


def test_provider_accepts_missing_annotation_for_durable_activity():
    binding = provider.CopilotSdkProvider().compile_binding(
        instructions="instructions",
        agent_name="orders",
        options={"client_factory": _Client, "model": "gpt-5"},
        annotation=inspect.Signature.empty,
        capabilities=AgentCapabilities(),
    )

    assert binding.agent_name == "orders"


def test_session_creation_error_keeps_cached_client_open(monkeypatch):
    binding = _compile()

    async def fail_create(self, **options):
        raise RuntimeError("session failed")

    monkeypatch.setattr(_Client, "create_session", fail_create)

    with pytest.raises(RuntimeError, match="session failed"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed


def test_binding_maps_discovered_skills_and_mcp(monkeypatch):
    monkeypatch.setenv("MCP_URL", "https://mcp.example.test")
    binding = _compile(
        capabilities=AgentCapabilities(
            skills=(
                SkillDefinition(Path("skills/inventory")),
                SkillDefinition(Path("skills/orders")),
            ),
            mcp_servers=(
                MCPServerDefinition(
                    "orders",
                    MCPHTTPConfig(
                        "$MCP_URL",
                        allowed_tools=("lookup",),
                        headers=(("X-Tenant", "%TENANT_ID%"),),
                    ),
                ),
            ),
        )
    )
    monkeypatch.setenv("TENANT_ID", "tenant-1")

    async def invoke():
        async with binding.open_agent(InvocationMetadata()):
            pass

    asyncio.run(invoke())

    options = _Client.created[0].session_options
    assert options["enable_skills"] is True
    assert options["skill_directories"] == ["skills"]
    assert options["mcp_servers"] == {
        "orders": {
            "type": "http",
            "url": "https://mcp.example.test",
            "headers": {"X-Tenant": "tenant-1"},
            "tools": ["lookup"],
        }
    }
    assert options["mcp_oauth_token_storage"] == "in-memory"
    assert list(options["available_tools"]) == ["builtin:skill", "mcp:*"]


@pytest.mark.parametrize(
    ("mcp_servers", "expected_available_tools"),
    [
        ({}, []),
        (
            {
                "custom": {
                    "type": "http",
                    "url": "https://custom.example.test/mcp",
                    "tools": ["lookup"],
                }
            },
            ["mcp:*"],
        ),
    ],
)
def test_explicit_mcp_servers_replace_discovered_servers(
    mcp_servers,
    expected_available_tools,
):
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "discovered",
                    MCPHTTPConfig("$MISSING_MCP_URL"),
                ),
            ),
        ),
        session_options={"mcp_servers": mcp_servers},
    )

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    options = _Client.created[0].session_options
    assert options["mcp_servers"] == mcp_servers
    assert list(options["available_tools"]) == expected_available_tools


def test_disabled_discovered_mcp_server_is_not_prepared():
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "inventory",
                    MCPHTTPConfig("$MISSING_INVENTORY_MCP_URL"),
                ),
            ),
        ),
        session_options={"disabled_mcp_servers": ["inventory"]},
    )

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    options = _Client.created[0].session_options
    assert options["mcp_servers"] == {}
    assert list(options["available_tools"]) == []


@pytest.mark.parametrize(
    ("available_tools", "expected_available_tools"),
    [
        (None, ["builtin:skill"]),
        (["builtin:custom"], ["builtin:custom"]),
    ],
)
def test_explicit_skill_configuration_uses_effective_available_tools(
    available_tools,
    expected_available_tools,
):
    session_options = {
        "enable_skills": True,
        "skill_directories": ["custom-skills"],
    }
    if available_tools is not None:
        session_options["available_tools"] = available_tools
    binding = _compile(session_options=session_options)

    asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    options = _Client.created[0].session_options
    assert options["enable_skills"] is True
    assert options["skill_directories"] == ["custom-skills"]
    assert list(options["available_tools"]) == expected_available_tools


def test_binding_allowlists_explicit_python_tools():
    binding = _compile(
        tools=Tool(
            name="lookup_order",
            description="Look up an order",
        )
    )

    async def invoke():
        async with binding.open_agent(InvocationMetadata()):
            pass

    asyncio.run(invoke())

    options = _Client.created[0].session_options
    assert list(options["available_tools"]) == ["custom:lookup_order"]


def test_mcp_credentials_require_https(monkeypatch):
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "orders",
                    MCPHTTPConfig(
                        "http://mcp.example.test",
                        headers=(("X-Key", "secret"),),
                    ),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="must use HTTPS"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed


def test_mcp_url_credentials_require_https():
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "orders",
                    MCPHTTPConfig("http://user:password@mcp.example.test/mcp"),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="must use HTTPS"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed


def test_mcp_url_query_requires_https():
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "orders",
                    MCPHTTPConfig(
                        "http://mcp.example.test/mcp?access_token=secret"
                    ),
                ),
            ),
        )
    )

    with pytest.raises(ValueError, match="must use HTTPS"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed


def test_cancellation_closes_session_but_keeps_cached_client_open(monkeypatch):
    async def cancel(self, prompt):
        raise asyncio.CancelledError

    monkeypatch.setattr(_Session, "send_and_wait", cancel)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed
    assert _Client.created[0].sessions[0].closed


@pytest.mark.parametrize(
    "response",
    [None, SimpleNamespace(data=object())],
)
def test_binding_rejects_missing_final_assistant_message(monkeypatch, response):
    async def send(self, prompt):
        return response

    monkeypatch.setattr(_Session, "send_and_wait", send)

    with pytest.raises(TypeError, match="final assistant message"):
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed
    assert _Client.created[0].sessions[0].closed


def test_binding_rejects_non_string_assistant_content(monkeypatch):
    class FakeAssistantMessageData:
        content = None

    async def send(self, prompt):
        return SimpleNamespace(data=FakeAssistantMessageData())

    monkeypatch.setattr(provider, "AssistantMessageData", FakeAssistantMessageData)
    monkeypatch.setattr(_Session, "send_and_wait", send)

    with pytest.raises(TypeError, match="content must be a string"):
        asyncio.run(_compile().run_agent("hello", InvocationMetadata()))

    assert not _Client.created[0].closed
    assert _Client.created[0].sessions[0].closed


@pytest.mark.parametrize("factory_kind", ["async_callable", "returns_awaitable"])
def test_binding_rejects_awaitable_factory_results(factory_kind):
    async def create_client():
        return _Client()

    if factory_kind == "async_callable":

        class AsyncFactory:
            async def __call__(self):
                return _Client()

        client_factory = AsyncFactory()
    else:
        client_factory = lambda: create_client()

    binding = _compile(client_factory=client_factory)

    with pytest.raises(TypeError, match="must return.*not an awaitable"):
        asyncio.run(binding.run_agent("hello", InvocationMetadata()))


def test_provider_rejects_async_factory_function():
    async def create_client():
        return _Client()

    with pytest.raises(TypeError, match="must be a synchronous function"):
        _compile(client_factory=create_client)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"unknown": True}, "Unsupported"),
        ({"tools": ["lookup"]}, "copilot.tools.Tool"),
        ({"session_provider": "custom"}, "ProviderConfig"),
    ],
)
def test_provider_rejects_unsupported_options(overrides, message):
    with pytest.raises(TypeError, match=message):
        _compile(**overrides)


def test_mcp_entra_token_is_injected_and_credential_is_closed(monkeypatch):
    import azure.identity.aio

    credentials = []

    class FakeCredential:
        def __init__(self, *, managed_identity_client_id):
            self.managed_identity_client_id = managed_identity_client_id
            self.scopes = []
            self.closed = False
            credentials.append(self)

        async def get_token(self, scope):
            self.scopes.append(scope)
            return SimpleNamespace(token="entra-token")

        async def close(self):
            self.closed = True

    monkeypatch.setattr(
        azure.identity.aio,
        "DefaultAzureCredential",
        FakeCredential,
    )
    monkeypatch.setenv("MCP_SCOPE", "api://inventory/.default")
    monkeypatch.setenv("MCP_CLIENT_ID", "client-id")
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "inventory",
                    MCPHTTPConfig(
                        "https://mcp.example.test",
                        auth=MCPAuthConfig(
                            scope="$MCP_SCOPE",
                            client_id="%MCP_CLIENT_ID%",
                        ),
                    ),
                ),
            ),
        )
    )

    async def invoke():
        async with binding.open_agent(InvocationMetadata()):
            assert not credentials[0].closed

    asyncio.run(invoke())

    assert credentials[0].managed_identity_client_id == "client-id"
    assert credentials[0].scopes == ["api://inventory/.default"]
    assert credentials[0].closed
    assert _Client.created[0].session_options["mcp_servers"]["inventory"] == {
        "type": "http",
        "url": "https://mcp.example.test",
        "headers": {"Authorization": "Bearer entra-token"},
        "tools": ["*"],
    }


def test_mcp_entra_cancellation_waits_for_token_acquisition_before_close(monkeypatch):
    import azure.identity.aio

    started = asyncio.Event()
    token_finished = False
    close_states = []

    class BlockingAsyncCredential:
        def __init__(self, *, managed_identity_client_id):
            pass

        async def get_token(self, scope):
            nonlocal token_finished
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                token_finished = True

        async def close(self):
            close_states.append(token_finished)

    monkeypatch.setattr(
        azure.identity.aio,
        "DefaultAzureCredential",
        BlockingAsyncCredential,
    )
    binding = _compile(
        capabilities=AgentCapabilities(
            mcp_servers=(
                MCPServerDefinition(
                    "inventory",
                    MCPHTTPConfig(
                        "https://mcp.example.test",
                        auth=MCPAuthConfig(scope="api://inventory/.default"),
                    ),
                ),
            ),
        )
    )

    async def cancel_during_token_acquisition():
        task = asyncio.create_task(
            binding.run_agent("hello", InvocationMetadata())
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_during_token_acquisition())

    assert close_states == [True]
