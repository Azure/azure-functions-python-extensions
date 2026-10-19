from __future__ import annotations

import asyncio
import inspect
import os
import re
import warnings
from collections.abc import Callable, Mapping, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any, AsyncIterator, TypedDict, cast, get_origin
from urllib.parse import urlsplit

from agent_framework import (
    Agent,
    BaseChatClient,
    ContextProvider,
    SkillsProvider,
    ToolTypes,
)
from agent_framework._feature_stage import ExperimentalWarning

from azurefunctions.agents.extensions.base import (
    AgentCapabilities,
    AgentProvider,
    CompiledAgent,
    InvocationMetadata,
    MCPServerDefinition,
    SkillDefinition,
)

AGENT_FRAMEWORK_PROVIDER_ID = "agent_framework"
ClientFactory = Callable[[], BaseChatClient[Any]]
type AgentTool = ToolTypes | Callable[..., Any]
_AGENT_ANNOTATION_TYPE = Agent
_ENV_REFERENCE = re.compile(
    r"\$([A-Za-z_][A-Za-z0-9_]*)|%([A-Za-z_][A-Za-z0-9_]*)%"
)

_SUPPORTED_OPTIONS = frozenset({"client_factory", "tools"})

if TYPE_CHECKING:
    from httpx import Request


@dataclass(frozen=True)
class _AgentFrameworkOptions:
    client_factory: ClientFactory
    tools: tuple[AgentTool, ...]


class _AgentKeywordOptions(TypedDict, total=False):
    context_providers: Sequence[ContextProvider]
    tools: Sequence[AgentTool]


@dataclass(frozen=True)
class AgentFrameworkBinding(CompiledAgent):
    instructions: str
    agent_name: str
    options: _AgentFrameworkOptions
    capabilities: AgentCapabilities

    def _create_agent(
        self,
        skills_provider: SkillsProvider | None,
        mcp_tools: Sequence[AgentTool],
    ) -> Agent[Any]:
        client = self.options.client_factory()
        if inspect.isawaitable(client):
            if inspect.iscoroutine(client):
                client.close()
            raise TypeError(
                "client_factory must return a BaseChatClient synchronously, "
                "not an awaitable"
            )
        options = _AgentKeywordOptions()
        if skills_provider is not None:
            options["context_providers"] = [skills_provider]
        tools = list(self.options.tools)
        if mcp_tools:
            options["tools"] = [*tools, *mcp_tools]
        elif tools:
            options["tools"] = tools
        return Agent(
            client=client,
            instructions=self.instructions,
            name=self.agent_name,
            **options,
        )

    @asynccontextmanager
    async def open_agent(
        self,
        invocation: InvocationMetadata,
    ) -> AsyncIterator[Agent[Any]]:
        async with AsyncExitStack() as stack:
            skills_provider = _build_skills_provider(self.capabilities.skills)
            mcp_tools = [
                await stack.enter_async_context(_open_mcp_tool(definition))
                for definition in self.capabilities.mcp_servers
            ]
            agent = self._create_agent(skills_provider, mcp_tools)
            entered_agent = await stack.enter_async_context(agent)
            yield entered_agent

    async def run_agent(
        self,
        prompt: str,
        invocation: InvocationMetadata,
    ) -> str:
        async with self.open_agent(invocation) as agent:
            response = await agent.run(prompt)
        text = getattr(response, "text", None)
        if not isinstance(text, str):
            raise TypeError("Microsoft Agent Framework response.text must be a string")
        return text


class AgentFrameworkProvider(AgentProvider):
    provider_id = AGENT_FRAMEWORK_PROVIDER_ID
    distribution_name = "azurefunctions-agents-extensions-agent-framework"
    supported_capabilities = frozenset({"skills", "mcp"})

    def compile_binding(
        self,
        *,
        instructions: str,
        agent_name: str,
        options: Mapping[str, object],
        annotation: object,
        capabilities: AgentCapabilities,
    ) -> AgentFrameworkBinding:
        unknown = sorted(set(options) - _SUPPORTED_OPTIONS)
        if unknown:
            raise TypeError(
                "Unsupported Microsoft Agent Framework option(s): " + ", ".join(unknown)
            )
        client_factory: object | None = options.get("client_factory")
        if client_factory is None:
            raise TypeError("client_factory option is required")
        if not callable(client_factory):
            raise TypeError("client_factory must be callable")
        if inspect.iscoroutinefunction(client_factory):
            raise TypeError("client_factory must be a synchronous function")
        if annotation is not inspect.Signature.empty:
            annotation_origin = get_origin(annotation)
            if (
                annotation is not _AGENT_ANNOTATION_TYPE
                and annotation_origin is not _AGENT_ANNOTATION_TYPE
            ):
                raise TypeError(
                    "Microsoft Agent Framework binding parameter must be annotated "
                    "as agent_framework.Agent"
                )

        return AgentFrameworkBinding(
            instructions=instructions,
            agent_name=agent_name,
            options=_AgentFrameworkOptions(
                client_factory=cast(ClientFactory, client_factory),
                tools=_normalize_tools(options.get("tools")),
            ),
            capabilities=capabilities,
        )


def _normalize_tools(value: object) -> tuple[AgentTool, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(cast(Sequence[AgentTool], value))
    return (value,)


def _build_skills_provider(
    skills: Sequence[SkillDefinition],
) -> SkillsProvider | None:
    if not skills:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ExperimentalWarning)
        return SkillsProvider.from_paths(
            [skill.path for skill in skills],
            disable_load_skill_approval=True,
            disable_read_skill_resource_approval=True,
        )


def _resolve_environment(value: str, *, field: str) -> str:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        resolved = os.environ.get(name)
        if resolved is None:
            missing.add(name)
            return match.group(0)
        return resolved

    result = _ENV_REFERENCE.sub(replace, value)
    if missing:
        raise ValueError(
            f"MCP {field} references missing environment variable(s): "
            f"{', '.join(sorted(missing))}"
        )
    return result


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    normalized = hostname.rstrip(".").casefold()
    if normalized == "localhost":
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


@asynccontextmanager
async def _open_mcp_tool(
    definition: MCPServerDefinition,
) -> AsyncIterator[AgentTool]:
    try:
        import mcp  # noqa: F401
        from agent_framework import MCPStreamableHTTPTool
        from httpx import AsyncClient
    except ImportError as error:
        raise ImportError(
            "MCP support is not installed. Install "
            "'azurefunctions-agents-extensions-agent-framework[mcp]'."
        ) from error

    config = definition.config
    url = _resolve_environment(config.url, field=f"server {definition.name!r} URL")
    parsed_url = urlsplit(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(
            f"MCP server {definition.name!r} URL must use HTTP or HTTPS"
        )
    static_headers = {
        name: _resolve_environment(
            value,
            field=f"server {definition.name!r} header {name!r}",
        )
        for name, value in config.headers
    }
    auth = config.auth
    scope = (
        _resolve_environment(
            auth.scope,
            field=f"server {definition.name!r} auth scope",
        )
        if auth is not None
        else None
    )
    client_id = (
        _resolve_environment(
            auth.client_id,
            field=f"server {definition.name!r} auth client_id",
        )
        if auth is not None and auth.client_id is not None
        else None
    )
    if (
        parsed_url.scheme == "http"
        and (static_headers or auth is not None)
        and not _is_loopback_host(parsed_url.hostname)
    ):
        raise ValueError(
            f"MCP server {definition.name!r} must use HTTPS when headers or auth "
            "are configured; HTTP is allowed only for loopback hosts"
        )

    async with AsyncExitStack() as stack:
        credential = None
        if scope is not None:
            try:
                from azure.identity import DefaultAzureCredential
            except ImportError as error:
                raise ImportError(
                    "MCP Entra authentication is not installed. Install "
                    "'azurefunctions-agents-extensions-agent-framework[mcp]'."
                ) from error
            credential = DefaultAzureCredential(
                managed_identity_client_id=client_id,
            )
            stack.callback(credential.close)

        http_client = None
        if static_headers or credential is not None:

            async def inject_headers(request: Request) -> None:
                for name, value in static_headers.items():
                    request.headers[name] = value
                if credential is not None and scope is not None:
                    token = await asyncio.to_thread(credential.get_token, scope)
                    request.headers["Authorization"] = f"Bearer {token.token}"

            http_client = await stack.enter_async_context(
                AsyncClient(
                    follow_redirects=False,
                    event_hooks={"request": [inject_headers]},
                )
            )

        tool = MCPStreamableHTTPTool(
            name=definition.name,
            url=url,
            tool_name_prefix=definition.name,
            allowed_tools=(
                list(config.allowed_tools)
                if config.allowed_tools is not None
                else None
            ),
            load_tools=True,
            load_prompts=False,
            http_client=http_client,
        )
        yield cast(AgentTool, tool)


def create_provider() -> AgentFrameworkProvider:
    return AgentFrameworkProvider()
