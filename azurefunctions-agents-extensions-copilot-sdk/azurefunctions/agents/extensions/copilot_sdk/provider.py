from __future__ import annotations

import asyncio
import inspect
import os
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, AsyncIterator, cast, get_origin
from urllib.parse import urlsplit

from copilot import CopilotClient
from copilot.session import (
    CopilotSession,
    MCPHTTPServerConfig,
    MCPStdioServerConfig,
    ProviderConfig,
    SystemMessageReplaceConfig,
)
from copilot.session_events import AssistantMessageData
from copilot.tools import Tool

from azurefunctions.agents.extensions.base import (
    AgentCapabilities,
    AgentProvider,
    CompiledAgent,
    InvocationMetadata,
    MCPServerDefinition,
    SkillDefinition,
)

COPILOT_SDK_PROVIDER_ID = "copilot_sdk"
ClientFactory = Callable[[], CopilotClient]
PermissionHandler = Callable[..., Any]
_ENV_REFERENCE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)|%([A-Za-z_][A-Za-z0-9_]*)%")

_SUPPORTED_OPTIONS = frozenset(
    {
        "client_factory",
        "model",
        "on_permission_request",
        "provider",
        "tools",
    }
)


@dataclass(frozen=True)
class _CopilotSdkOptions:
    client_factory: ClientFactory
    model: str
    on_permission_request: PermissionHandler | None
    provider: ProviderConfig | None
    tools: tuple[Tool, ...]


@dataclass(frozen=True)
class CopilotSdkBinding(CompiledAgent):
    instructions: str
    agent_name: str
    options: _CopilotSdkOptions
    capabilities: AgentCapabilities

    @asynccontextmanager
    async def open_agent(
        self,
        invocation: InvocationMetadata,
    ) -> AsyncIterator[CopilotSession]:
        client = self.options.client_factory()
        if inspect.isawaitable(client):
            if inspect.iscoroutine(client):
                client.close()
            raise TypeError(
                "client_factory must return a CopilotClient synchronously, "
                "not an awaitable"
            )
        if not isinstance(client, CopilotClient):
            raise TypeError("client_factory must return a CopilotClient")

        async with AsyncExitStack() as stack:
            entered_client = await stack.enter_async_context(client)
            mcp_servers = await _build_mcp_servers(
                self.capabilities.mcp_servers,
                stack,
            )
            skill_directories = _skill_directories(self.capabilities.skills)
            session = await entered_client.create_session(
                model=self.options.model,
                tools=list(self.options.tools),
                system_message=SystemMessageReplaceConfig(
                    mode="replace",
                    content=self.instructions,
                ),
                provider=self.options.provider,
                on_permission_request=self.options.on_permission_request,
                streaming=False,
                enable_config_discovery=False,
                enable_session_telemetry=False,
                request_extensions=False,
                enable_session_store=False,
                included_builtin_skills=[],
                enable_skills=bool(skill_directories),
                skill_directories=skill_directories,
                mcp_servers=mcp_servers,
                mcp_oauth_token_storage="in-memory",
                skip_custom_instructions=True,
                tool_search={"enabled": False},
                infinite_sessions={"enabled": False},
                memory={"enabled": False},
            )
            entered_session = await stack.enter_async_context(session)
            yield entered_session

    async def run_agent(
        self,
        prompt: str,
        invocation: InvocationMetadata,
    ) -> str:
        async with self.open_agent(invocation) as session:
            response = await session.send_and_wait(prompt)
        if response is None or not isinstance(response.data, AssistantMessageData):
            raise TypeError(
                "GitHub Copilot SDK response must contain a final assistant message"
            )
        if not isinstance(response.data.content, str):
            raise TypeError("GitHub Copilot SDK response content must be a string")
        return response.data.content


class CopilotSdkProvider(AgentProvider):
    provider_id = COPILOT_SDK_PROVIDER_ID
    distribution_name = "azurefunctions-agents-extensions-copilot-sdk"
    supported_capabilities = frozenset({"skills", "mcp"})

    def compile_binding(
        self,
        *,
        instructions: str,
        agent_name: str,
        options: Mapping[str, object],
        annotation: object,
        capabilities: AgentCapabilities,
    ) -> CopilotSdkBinding:
        unknown = sorted(set(options) - _SUPPORTED_OPTIONS)
        if unknown:
            raise TypeError(
                "Unsupported GitHub Copilot SDK option(s): " + ", ".join(unknown)
            )
        client_factory = options.get("client_factory")
        if client_factory is None:
            raise TypeError("client_factory option is required")
        if not callable(client_factory):
            raise TypeError("client_factory must be callable")
        if inspect.iscoroutinefunction(client_factory):
            raise TypeError("client_factory must be a synchronous function")

        model = options.get("model")
        if not isinstance(model, str) or not model.strip():
            raise TypeError("model option must be a non-empty string")
        if annotation is not inspect.Signature.empty:
            annotation_origin = get_origin(annotation)
            if (
                annotation is not CopilotSession
                and annotation_origin is not CopilotSession
            ):
                raise TypeError(
                    "GitHub Copilot SDK binding parameter must be annotated "
                    "as copilot.session.CopilotSession"
                )

        permission_handler = options.get("on_permission_request")
        if permission_handler is not None and not callable(permission_handler):
            raise TypeError("on_permission_request must be callable")
        provider = options.get("provider")
        if provider is not None and not isinstance(provider, Mapping):
            raise TypeError("provider must be a Copilot SDK ProviderConfig mapping")

        return CopilotSdkBinding(
            instructions=instructions,
            agent_name=agent_name,
            options=_CopilotSdkOptions(
                client_factory=cast(ClientFactory, client_factory),
                model=model.strip(),
                on_permission_request=cast(
                    PermissionHandler | None,
                    permission_handler,
                ),
                provider=cast(ProviderConfig | None, provider),
                tools=_normalize_tools(options.get("tools")),
            ),
            capabilities=capabilities,
        )


def _normalize_tools(value: object) -> tuple[Tool, ...]:
    if value is None:
        return ()
    tools = (
        tuple(cast(Sequence[object], value))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
        else (value,)
    )
    if any(not isinstance(tool, Tool) for tool in tools):
        raise TypeError("tools must contain only copilot.tools.Tool values")
    return cast(tuple[Tool, ...], tools)


def _skill_directories(skills: Sequence[SkillDefinition]) -> list[str]:
    return sorted({str(skill.path.parent) for skill in skills})


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


async def _build_mcp_servers(
    definitions: Sequence[MCPServerDefinition],
    stack: AsyncExitStack,
) -> dict[str, MCPStdioServerConfig | MCPHTTPServerConfig]:
    servers: dict[str, MCPStdioServerConfig | MCPHTTPServerConfig] = {}
    for definition in definitions:
        config = definition.config
        url = _resolve_environment(
            config.url,
            field=f"server {definition.name!r} URL",
        )
        parsed_url = urlsplit(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(
                f"MCP server {definition.name!r} URL must use HTTP or HTTPS"
            )
        headers = {
            name: _resolve_environment(
                value,
                field=f"server {definition.name!r} header {name!r}",
            )
            for name, value in config.headers
        }
        if (
            parsed_url.scheme == "http"
            and (headers or config.auth is not None)
            and not _is_loopback_host(parsed_url.hostname)
        ):
            raise ValueError(
                f"MCP server {definition.name!r} must use HTTPS when headers or auth "
                "are configured; HTTP is allowed only for loopback hosts"
            )
        if config.auth is not None:
            try:
                from azure.identity import DefaultAzureCredential
            except ImportError as error:
                raise ImportError(
                    "MCP Entra authentication is not installed. Install "
                    "'azurefunctions-agents-extensions-copilot-sdk[mcp]'."
                ) from error
            scope = _resolve_environment(
                config.auth.scope,
                field=f"server {definition.name!r} auth scope",
            )
            client_id = (
                _resolve_environment(
                    config.auth.client_id,
                    field=f"server {definition.name!r} auth client_id",
                )
                if config.auth.client_id is not None
                else None
            )
            credential = DefaultAzureCredential(
                managed_identity_client_id=client_id,
            )
            stack.callback(credential.close)
            token = await asyncio.to_thread(credential.get_token, scope)
            headers["Authorization"] = f"Bearer {token.token}"

        servers[definition.name] = MCPHTTPServerConfig(
            type="http",
            url=url,
            headers=headers,
            tools=(
                list(config.allowed_tools)
                if config.allowed_tools is not None
                else ["*"]
            ),
        )
    return servers


def create_provider() -> CopilotSdkProvider:
    return CopilotSdkProvider()
