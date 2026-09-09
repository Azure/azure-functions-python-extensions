"""Execution-time adapter between markdown recipes and DAFX agent entities."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Sequence
from typing import Any, Literal, overload

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    AgentSession,
    ResponseStream,
)

from azurefunctions.agents.extensions.base import InvocationMetadata

from .provider import AgentFrameworkBinding


class MarkdownDurableAgent:
    """Register a recipe, not a live client, with DAFX.

    Every entity run opens a fresh agent and resources on the execution loop.
    No clients, MCP connections, or per-run session objects are cached here.
    """

    def __init__(self, binding: AgentFrameworkBinding) -> None:
        self._binding = binding
        self.name: str | None = binding.agent_name
        self.id = f"markdown:{self.name}"
        self.description: str | None = None

    def create_session(self, *, session_id: str | None = None) -> AgentSession:
        return AgentSession(session_id=session_id)

    def get_session(
        self, service_session_id: Any, *, session_id: str | None = None
    ) -> AgentSession:
        return AgentSession(
            service_session_id=service_session_id, session_id=session_id
        )

    @overload
    def run(
        self, messages: Any = None, *, stream: Literal[False] = False,
        session: AgentSession | None = None, **kwargs: Any,
    ) -> Awaitable[AgentResponse[Any]]:
        ...

    @overload
    def run(
        self, messages: Any = None, *, stream: Literal[True],
        session: AgentSession | None = None, **kwargs: Any,
    ) -> ResponseStream[AgentResponseUpdate, AgentResponse[Any]]:
        ...

    def run(
        self, messages: Any = None, *, stream: bool = False,
        session: AgentSession | None = None, **kwargs: Any,
    ) -> Awaitable[AgentResponse[Any]] | ResponseStream[
        AgentResponseUpdate, AgentResponse[Any]
    ]:
        invocation = InvocationMetadata(function_name=f"dafx-{self.name}")

        async def invoke() -> AgentResponse[Any]:
            async with self._binding.open_agent(invocation) as agent:
                response = await agent.run(messages, session=session, **kwargs)
                if not isinstance(response, AgentResponse):
                    raise TypeError("A durable agent must return AgentResponse.")
                return response

        if not stream:
            return invoke()

        final: AgentResponse[Any] | None = None

        async def updates() -> AsyncGenerator[AgentResponseUpdate, None]:
            nonlocal final
            async with self._binding.open_agent(invocation) as agent:
                inner = agent.run(messages, stream=True, session=session, **kwargs)
                async for update in inner:
                    yield update
                # Finalization can run provider hooks. Keep resources alive until
                # it completes and preserve the complete response, not just text.
                final = await inner.get_final_response()

        def finalize(_: Sequence[AgentResponseUpdate]) -> AgentResponse[Any]:
            if final is None:
                raise RuntimeError("The durable agent stream did not complete.")
            return final

        iterator = updates()
        return ResponseStream(
            iterator, finalizer=finalize, cleanup_hooks=[iterator.aclose]
        )
