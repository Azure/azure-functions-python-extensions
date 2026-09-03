from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, AsyncIterator, get_origin

from agent_framework import Agent, BaseChatClient

from azurefunctions.extensions.agents.base import InvocationMetadata

AGENT_FRAMEWORK_PROVIDER_ID = "agent_framework"
ClientFactory = Callable[[], BaseChatClient[Any]]
_AGENT_ANNOTATION_TYPE = Agent

_SUPPORTED_OPTIONS = frozenset(
    {
        "additional_properties",
        "client_factory",
        "compaction_strategy",
        "context_providers",
        "default_options",
        "description",
        "middleware",
        "require_per_service_call_history_persistence",
        "tokenizer",
        "tools",
    }
)


@dataclass(frozen=True)
class AgentFrameworkBinding:
    instructions: str
    agent_name: str
    client_factory: ClientFactory
    agent_options: Mapping[str, Any]

    def _create_agent(self) -> Agent[Any]:
        return Agent(
            client=self.client_factory(),
            instructions=self.instructions,
            name=self.agent_name,
            **self.agent_options,
        )

    @asynccontextmanager
    async def open_agent(
        self,
        invocation: InvocationMetadata,
    ) -> AsyncIterator[Agent[Any]]:
        async with self._create_agent() as agent:
            yield agent

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


class AgentFrameworkProvider:
    provider_id = AGENT_FRAMEWORK_PROVIDER_ID
    distribution_name = "azurefunctions-extensions-agents-framework"

    def compile_binding(
        self,
        *,
        instructions: str,
        agent_name: str,
        options: Mapping[str, Any],
        annotation: Any,
    ) -> AgentFrameworkBinding:
        unknown = sorted(set(options) - _SUPPORTED_OPTIONS)
        if unknown:
            raise TypeError(
                "Unsupported Microsoft Agent Framework option(s): " + ", ".join(unknown)
            )
        client_factory = options.get("client_factory")
        if client_factory is None:
            raise TypeError("client_factory option is required")
        if not callable(client_factory):
            raise TypeError("client_factory must be callable")
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

        agent_options = dict(options)
        del agent_options["client_factory"]
        return AgentFrameworkBinding(
            instructions=instructions,
            agent_name=agent_name,
            client_factory=client_factory,
            agent_options=MappingProxyType(agent_options),
        )


def create_provider() -> AgentFrameworkProvider:
    return AgentFrameworkProvider()
